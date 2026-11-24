# Linux: build the port and the server, and play co-op

The native Linux port (#571, #598) builds and runs from source. There is no Linux release yet,
so a Linux player builds the game, the launcher's co-op page runs it, and a Linux host builds
shadnet as well. Windows players use the release as usual; a Linux player and a Windows player
play together when both run the **same release version** (below).

Played on CachyOS (Arch) with an NVIDIA GTX 1070 (driver 580), clang 23 and Qt 6.12: a Linux
host (v1.5.0 with #598, shadnet built as below) and a Windows player on the v1.5.0 release, in one
team over a virtual LAN, for several hours. The launcher's setup made event files identical to
v1.5.0's `event-reference.json`.

## Packages

| What | Arch | Notes |
|---|---|---|
| Port | `clang cmake ninja pkgconf vulkan-headers vulkan-icd-loader fmt boost robin-map xxhash sdl3 ffmpeg protobuf nlohmann-json openssl zlib glslang spirv-tools libx11` | clang: GCC 13 lacks deducing `this`. Vulkan headers 1.4.33x or newer (`VK_VALVE_shader_mixed_float_dot_product`) |
| Zydis, VMA | nothing | Without a system package the port builds them from the emulator's submodules (`build.sh` checks them out) |
| Launcher | `python tk` | The launcher is Tkinter. Without `tk` it exits at once and only `bbport/user/log/launcher-errors.txt` says why |
| Server (host only) | `qt6-base qt6-httpserver qt6-websockets` | Qt 6.8 or newer: `src/webapi_server.cpp` needs 6.8's QHttpServer API (Ubuntu 24.04's 6.4 does not build it) |

## Build

Only these submodules are needed (the emulator's full recursive set is not):

```bash
git clone https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together.git
cd BBSC-Yharnam-Together
git submodule update --init --depth 1 bbport/gpu/third_party/fsr-vulkan bbport/gpu/third_party/imgui \
    bbport/third_party/LibAtrac9 bbport/gpu/third_party/magic_enum bbport/gpu/third_party/miniz \
    bbport/gpu/third_party/xbyak server/externals/protobuf
cd bbport
CC=clang CXX=clang++ BB_PRODUCTION=1 bash build.sh     # out/bb-probe and out/gpu/libbbgpu.so
```

`BB_PRODUCTION=1` builds what a release ships (no cheats, save editor or debug tools); leave it
out for a development build.

Memory: ninja runs one compile per core, and with link-time optimization (`BB_LTO`, on by
default) the build can take more than 4 GB. On a machine with little RAM, or in a cgroup with a
memory limit, it is killed and stops with `ninja: build stopped: interrupted by user`; build with
`BB_LTO=OFF` and fewer jobs (a `ninja` earlier on `PATH` that runs `/usr/bin/ninja -j3 "$@"`).

The host also builds shadnet (it fetches abseil while configuring):

```bash
cd ../server
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
ninja -C build shadnet
cp worlds.cfg scoreboards.cfg build/
```

The launcher finds shadnet in `server/build` when `bbport/server` has none, and starts it with
the release version from `bbport/VERSION.txt` (below), so the games of that release are let in.
Copy the release's `server/shadnet.cfg` into `server/build` with `BackendFolder=../../backend`.

## Make it a co-op install

The launcher shows its co-op page in a release folder: one with `event-reference.json` beside the
launcher. From the Windows release of the same version (the portable zip), copy into `bbport/`:

- `event-reference.json` (the tested event files' hashes: setup compares the player's with them);
- `VERSION.txt` (the release's version: the server refuses another release);
- `tools/party_boss_events.py` (the same file as `tools/re/party_boss_events.py`).

`party_boss_events.py` from the zip has CRLF line endings; `sed -i 's/\r$//'` makes it
identical to the source's.

Then start the launcher with the system Python:

```bash
cd bbport
python3 launcher/bbport_launcher_win.py
```

The Co-op page is the same as on Windows: the game folder (the dump with the 1.09 update), host or
guest, the host's address. The host's PLAY starts shadnet and the backend first.

## Playing with Windows players

shadnet compares each game's build with its own: another **version** or **protocol** is refused,
any other difference (another revision, other files) only shows a warning. So a Linux build of
the same release plays with that release on Windows.

Until a release has the Linux port, build the release's tag with the port applied on top:

```bash
git fetch --unshallow origin 2>/dev/null; git fetch origin tag v1.5.0
git worktree add ../yt-v1.5.0 v1.5.0
cd ../yt-v1.5.0
git diff 85b02ee7 63b57800 | git apply -3       # #598, the Linux port; applies cleanly on v1.5.0
```

and give the build the release's version: `BB_RELEASE_VERSION=v1.5.0` for `build.sh`, and the
release's `VERSION.txt` as above. shadnet's log then names `version=1.5.0` and `protocol=9`.

## Performance and known issues (NVIDIA)

- On NVIDIA the port keeps copies of the game's memory (the *new memory and translation model*
  needs an AMD GPU), so expect a few percent less than the upstream port 0.7 at the same
  settings. A GTX 1070 holds 57–60 FPS at 2560x1440 with FSR 3.1 *Performance* (1280x720 scene) and
  the game's effects on; *Balanced* gave ~49 FPS, *Quality* ~40. Model LOD *Highest* cost ~6 FPS.
- Turn the game's own anti-aliasing off with FSR (it is on by default here); FSR anti-aliases.
- Stretched, flickering polygons on a 6–8 GB card: the texture cache's marks come from the VRAM
  heap at startup on Linux (1792 / 3584 MiB on 8 GB), the game stays over them and textures in
  use are evicted (about 228 000 in one session here). #603 takes the marks from the driver's live
  budget, as on Windows; with it applied the glitches were gone. Programs holding VRAM (an
  animated wallpaper, browsers) lower that budget: close them while playing.
- `ray_traced_ao` needs ray tracing hardware; leave it off on GTX 10xx.

## Reaching the host

As on Windows (README, *Play it*): the same VPN (Radmin VPN, Tailscale, ZeroTier or any virtual
LAN) or the host's public IP with the ports forwarded. A Linux host with a firewall (ufw,
firewalld) opens those ports itself; the launcher only handles Windows Firewall.
