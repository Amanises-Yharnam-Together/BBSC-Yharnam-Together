# SPDX-License-Identifier: GPL-2.0-or-later
"""The support bundle (Kaniel 2026-10-25): one zip with what a bug report needs, made by the launcher's
Support bundle button, while the game runs too. It holds the logs (the game's, the co-op server's, the
launcher's, the co-op traces), the crash and freeze reports, the settings and a network check. It never
holds a save, a game file or the player's secret: coop.json's password is left out, and in the
launcher's own texts the user folder's path shows as %USERPROFILE%.

The game keeps writing its logs while the bundle copies them (their files are shared for reading), so a
bundle made in the middle of a session has everything up to that moment. Zipping runs at background
priority (worker_priority): the game's frame rate comes first."""
import json
import os
import platform
import socket
import sys
import time
import zipfile
from pathlib import Path, PureWindowsPath

import bbport_coop

# The newest few of each kind: a trace can reach 50 MB (TraceFileCap) and a dump a few MB.
KEPT_TRACES = 3
KEPT_DUMPS = 3
# What the zip leaves out of user\log: what we sent already is noted, not news.
SKIPPED_LOG_NAMES = {bbport_coop.REPORTS_SENT}
SECRET_KEYS = ('password',)
LEFT_OUT = '(left out)'


def bundle_name(now=None):
    """'Yharnam Together support 20261025-120000.zip', in local time."""
    return time.strftime('Yharnam Together support %Y%m%d-%H%M%S.zip', time.localtime(now))


def known_desktop():
    """The Desktop Windows shows (its known folder, which OneDrive or a policy may have moved), or None."""
    if os.name != 'nt':
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class Guid(ctypes.Structure):
            _fields_ = [('a', wintypes.DWORD), ('b', wintypes.WORD), ('c', wintypes.WORD), ('d', ctypes.c_ubyte * 8)]

        # FOLDERID_Desktop {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
        desktop = Guid(0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41))
        path = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(desktop), 0, None, ctypes.byref(path)) != 0:
            return None
        try:
            return path.value
        finally:
            ctypes.windll.ole32.CoTaskMemFree(path)
    except (OSError, AttributeError, ValueError):
        return None


def reveal_command(target, windows_dir):
    """Explorer's command line that opens the zip's folder with the zip selected. A string, not a list: a list
    quotes the whole "/select,<path>" switch (the name has spaces), which Explorer does not read, and it opened
    its default folder instead (Kaniel 2026-11-01)."""
    return f'"{PureWindowsPath(windows_dir) / "explorer.exe"}" /select,"{PureWindowsPath(target)}"'


def default_folder(home=None, known_desktop=None):
    """Where the zip goes: the Desktop Windows shows, else %USERPROFILE%\\Desktop (OneDrive's too), else the
    home folder. Kaniel 2026-11-01: with a moved Desktop an empty %USERPROFILE%\\Desktop can still be there."""
    if known_desktop is None and home is None:
        known_desktop = globals()['known_desktop']()
    if known_desktop and Path(known_desktop).is_dir():
        return Path(known_desktop)
    home = Path(home or Path.home())
    for desktop in (home / 'Desktop', home / 'OneDrive' / 'Desktop'):
        if desktop.is_dir():
            return desktop
    return home


def newest(paths, kept):
    return sorted(paths, key=lambda path: path.stat().st_mtime)[-kept:] if kept else []


def log_files(log):
    """user\\log's files for the bundle as (path, name in the zip): every log and report, the older runs'
    logs, and only the newest KEPT_TRACES co-op traces and KEPT_DUMPS crash and freeze dumps."""
    log = Path(log)
    if not log.is_dir():
        return []
    files = [path for path in log.iterdir() if path.is_file() and path.name not in SKIPPED_LOG_NAMES]
    traces = [path for path in files if path.name.startswith('coop-trace-')]
    dumps = [path for path in files if path.suffix == '.dmp']
    chosen = [path for path in files if path not in traces and path not in dumps]
    chosen += newest(traces, KEPT_TRACES)
    for kind in ('crash-', 'freeze-'):
        chosen += newest([path for path in dumps if path.name.startswith(kind)], KEPT_DUMPS)
    found = [(path, f'log/{path.name}') for path in sorted(chosen)]
    older = log / 'older'
    if older.is_dir():
        found += [(path, f'log/older/{path.name}') for path in sorted(older.iterdir()) if path.is_file()]
    return found


def without_secrets(settings):
    """coop.json's settings with the password replaced: the player id stays (the server's log names it)."""
    return {key: (LEFT_OUT if key in SECRET_KEYS and value else value) for key, value in settings.items()}


def hide_home(text, home=None):
    home = str(home or Path.home())
    return text.replace(home, '%USERPROFILE%') if home and home not in ('/', '\\') else text


def port_answers(host, port, timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def network_report(settings, answers=port_answers, addresses=None, this_pc=None):
    """What the co-op connection looks like from this PC: the host's address, whether this PC is the
    host, this PC's addresses and VPNs, and whether the host's server ports answer."""
    host = str(settings.get('host_ip', ''))
    addresses = bbport_coop.own_addresses() if addresses is None else addresses
    hosting = bbport_coop.is_this_pc(host) if this_pc is None else this_pc
    lines = [f"Host's IP address: {host or '(not set)'}" + (f' ({bbport_coop.vpn_name(host)})'
                                                            if bbport_coop.vpn_name(host) else ''),
             f'This PC hosts: {"yes" if hosting else "no"}',
             f'This PC\'s addresses: {", ".join(addresses) or "(none found)"}',
             f'VPNs on this PC: {", ".join(f"{name} {ip}" for name, ip in bbport_coop.vpn_addresses(addresses)) or "none"}']
    if bbport_coop.valid_ip(host):
        for name, port in (('co-op server (shadnet)', bbport_coop.SHADNET_PORT),
                           ('reports and web API', bbport_coop.WEBAPI_PORT),
                           ("the game's server port", bbport_coop.BACKEND_PORT)):
            lines.append(f'{name}, TCP {port}: {"answers" if answers(host, port) else "no answer"}')
    return '\n'.join(lines) + '\n'


# Where Windows lists the Vulkan layers every Vulkan game loads by itself (overlays: Discord, Steam, RTSS,
# OBS, GeForce, HudSight...): each value names a layer's manifest, its data 0 when the layer is on.
IMPLICIT_LAYER_KEYS = (r'SOFTWARE\Khronos\Vulkan\ImplicitLayers', r'SOFTWARE\WOW6432Node\Khronos\Vulkan\ImplicitLayers')


def registry_layers():
    """[(manifest path, data)] from both hives' ImplicitLayers keys; none off Windows."""
    try:
        import winreg
    except ImportError:
        return []
    entries = []
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for path in IMPLICIT_LAYER_KEYS:
            try:
                with winreg.OpenKey(hive, path) as key:
                    index = 0
                    while True:
                        try:
                            name, data, _ = winreg.EnumValue(key, index)
                        except OSError:
                            break
                        entries.append((str(name), data))
                        index += 1
            except OSError:
                continue
    return entries


def vulkan_layers(read=registry_layers):
    """[(layer name or '?', manifest path, on)]: the overlays' Vulkan layers the game will load (Kaniel
    2026-11-01: players said an overlay stops them joining, and no log said which)."""
    layers = []
    try:
        entries = read()
    except OSError:
        return layers
    for manifest, data in entries:
        name = '?'
        try:
            layer = json.loads(Path(manifest).read_text(encoding='utf-8', errors='replace')).get('layer') or {}
            name = str(layer.get('name') or '?')
        except (OSError, ValueError, AttributeError):
            pass
        layers.append((name, manifest, data == 0))
    return layers


# Overlay and capture tools whose Vulkan layer crashes the game while it makes its device, before the first
# frame: (tool, the loader glob of its layer, what its layer's name or manifest path holds, lower case).
#   HudSight (a crosshair overlay): VK_LAYER_HudSight2 in vulkan-1.dll+0x45a10 under hudsightvk64.dll, and
#     XeSS's device setup through it; a player's game closed on every start (2026-10-25).
#   FPS Monitor: a player's game closed on every start until fpsmonvk64.json in FPS Monitor\tools was
#     renamed (Discord 2026-11-01).
#   Bandicam: the game did not start while it was installed and running (Discord 2026-10-24).
#   GOG Galaxy's overlay: support had players turn it off (Discord 2026-11-05); it has no use in this game.
CRASHING_OVERLAYS = (
    ('HudSight', '*HudSight*', ('hudsight',)),
    ('FPS Monitor', '*fpsmon*', ('fpsmon', 'fps monitor')),
    ('Bandicam', '*bandicam*', ('bandicam', 'bdcam')),
    ('GOG Galaxy overlay', '*GalaxyOverlay*', ('galaxyoverlay', 'galaxy_overlay', 'gog.com', 'gog galaxy')),
)
CRASHING_VK_LAYERS = tuple(glob for _tool, glob, _marks in CRASHING_OVERLAYS)
# The graphics drivers' own layers (laptop GPU switching, the driver's frame pacing): never an overlay.
DRIVER_LAYER_PREFIXES = ('vk_layer_nv_', 'vk_layer_amd_', 'vk_layer_intel_')


def loader_skips(name, globs):
    """Whether the Vulkan loader leaves the layer NAME out for these VK_LOADER_LAYERS_DISABLE globs (it
    compares without case; ~implicit~ and ~all~ name every overlay layer)."""
    import fnmatch
    name = name.lower()
    return any(glob.lower() in ('~implicit~', '~all~') or fnmatch.fnmatchcase(name, glob.lower()) for glob in globs)


def crashing_overlay(name, manifest):
    """The tool of CRASHING_OVERLAYS a layer belongs to, by its name or its manifest's path, or None."""
    text = f'{name}\n{manifest}'.lower()
    for tool, _glob, marks in CRASHING_OVERLAYS:
        if any(mark in text for mark in marks):
            return tool
    return None


def layers_to_skip(inherited, layers):
    """VK_LOADER_LAYERS_DISABLE for a game run: what was set already, the known crashers' globs, and the
    installed crashers' layers by their own names (LAYERS as vulkan_layers() gives them) in case a new
    version of a tool named its layer differently."""
    skipped = [item for item in inherited.split(',') if item]
    skipped += [glob for glob in CRASHING_VK_LAYERS if glob not in skipped]
    for name, manifest, on in layers:
        if on and name != '?' and crashing_overlay(name, manifest) and not loader_skips(name, skipped):
            skipped.append(name)
    return ','.join(skipped)


def overlay_suspects(layers, disabled):
    """The other tools' layers the game still loaded (on, not skipped, not the graphics driver's): what a
    game that closed while starting may blame. A layer whose manifest could not be read shows its path."""
    globs = [item for item in disabled.split(',') if item]
    suspects = []
    for name, manifest, on in layers:
        if not on or name.lower().startswith(DRIVER_LAYER_PREFIXES):
            continue
        if name == '?':
            if not loader_skips('', [glob for glob in globs if glob.startswith('~')]):
                suspects.append(manifest)
        elif not loader_skips(name, globs):
            suspects.append(name)
    return suspects


# run.py prints this just before it starts the game's executable: a run that ends before it failed in the
# preparation (mods, patches), where no Vulkan layer is loaded.
GAME_STARTING_LINE = 'run.py: starting the game'


def start_crash_suspects(code, started, was_up, stopped, layers, disabled, reshade=False):
    """What to name to the player after a game run: the suspects when the game's executable STARTED and
    closed by itself with an error before its window was ready (not after Stop, not after a clean exit),
    else nothing. RESHADE: the launcher's own ReShade layer was on for the run."""
    if code == 0 or not started or was_up or stopped:
        return []
    return (['ReShade'] if reshade else []) + overlay_suspects(layers, disabled)


def overlay_log_line(layers, disabled):
    """The game log's first line: the overlay layers, those the launcher skips (DISABLED, the
    VK_LOADER_LAYERS_DISABLE globs) and those switched off marked."""
    globs = [item for item in disabled.split(',') if item]
    parts = []
    for name, manifest, on in layers:
        text = name if name != '?' else f'? ({manifest})'
        if not on:
            text += ' (off)'
        elif loader_skips(name, globs):
            text += ' (skipped)'
        parts.append(text)
    return f'Launcher: Vulkan overlay layers: {", ".join(parts) or "none"}\n'


def system_report(versions, now=None, layers=None):
    """The launcher's and the release's versions, Windows, Python, the CPU and the Vulkan overlay layers."""
    lines = [f'Made: {time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(now))}']
    lines += [f'{name}: {value}' for name, value in versions.items()]
    lines += [f'System: {platform.platform()}', f'Machine: {platform.machine()}',
              f'Processor: {platform.processor() or "?"}', f'CPU threads: {os.cpu_count()}',
              f'Python: {sys.version.split()[0]}']
    layers = vulkan_layers() if layers is None else layers
    if not layers:
        lines.append('Vulkan overlay layers: none')
    else:
        lines.append(f'Vulkan overlay layers ({len(layers)}):')
        lines += [f'  {name} {"on" if on else "off"} ({manifest})' for name, manifest, on in layers]
    return '\n'.join(lines) + '\n'


def worker_priority():
    """Background priority for the calling thread on Windows (CPU and disk), so zipping never takes
    time from the game."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        THREAD_MODE_BACKGROUND_BEGIN = 0x00010000
        ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(),
                                                 THREAD_MODE_BACKGROUND_BEGIN)
    except (AttributeError, OSError):
        pass


def make_bundle(destination, user_dir, settings=None, extra_files=(), texts=None, home=None):
    """Writes the zip to DESTINATION and returns what it could not read as [(name, reason)].

    USER_DIR is the install's user folder (its log folder, coop.json, host_overrides.custom.json);
    SETTINGS the co-op settings (their password is left out); EXTRA_FILES more (path, name in the zip),
    such as bbport.ini; TEXTS {name: text} written as they are (the launcher's log, system.txt,
    network.txt). Missing files are skipped quietly; a file that cannot be read is listed in
    missing.txt inside the zip, and returned."""
    user_dir = Path(user_dir)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = log_files(user_dir / 'log')
    for name in ('last_run.log', 'host_overrides.custom.json'):
        if (user_dir / name).is_file():
            files.append((user_dir / name, name))
    files += [(Path(path), name) for path, name in extra_files if Path(path).is_file()]
    texts = dict(texts or {})
    if settings is not None:
        texts['coop.json'] = json.dumps(without_secrets(settings), indent=2) + '\n'
    failed = []
    partial = destination.with_name(destination.name + '.part')
    with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for name, text in texts.items():
            bundle.writestr(name, hide_home(text, home))
        for path, name in files:
            try:
                bundle.write(path, name)
            except OSError as error:  # a dump still being written, an antivirus holding the file
                failed.append((name, error.strerror or str(error)))
        if failed:
            bundle.writestr('missing.txt', ''.join(f'{name}: {reason}\n' for name, reason in failed))
    os.replace(partial, destination)
    return failed
