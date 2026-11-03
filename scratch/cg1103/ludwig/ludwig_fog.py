"""Ludwig's fog (m34): which events show or hide fog and walls, and the arena's fog events in full.

Usage: ludwig_fog.py <out dir> <name>=<event file> ...
For each file:
  walls.txt   every event with an object (2005:x), SFX (2006:x), character enable (2004:2) or
              multiplayer-state (3:6) instruction, and every InitializeEvent (2000:x) that names
              common event 7600-7699 (the multiplayer walls), with the object and SFX arguments
  arena.txt   in full, the events 13404700-13404899 and every event that names a flag
              13404742, 13404799 or 13404800-13404811 in its arguments
"""
import pathlib
import struct
import sys

sys.path.insert(0, r"C:\bb\release-src\tools\re")
import party_boss_events as pbe  # noqa: E402

ARENA_FLAGS = {13404742, 13404799, *range(13404800, 13404812), 13401800}
WALL_BANKS = {2005, 2006}


def words(args: bytes) -> list[int]:
    return list(struct.unpack_from(f"<{len(args) // 4}i", args)) if len(args) >= 4 else []


def line(k: int, instruction) -> str:
    bank, ident, length, layer, args = instruction
    layer_text = "" if layer in (-1, 0xFFFFFFFF) else f" layer={layer}"
    return f"  {k:2d} {bank}:{ident:<4d}{layer_text} args={words(args)} hex={args.hex()}"


def event_text(event) -> str:
    lines = [f"event {event['id']} rest={event['rest']} ({len(event['instructions'])} instructions)"]
    lines += [line(k, i) for k, i in enumerate(event["instructions"])]
    lines += [f"  param instr={p[0]} dst_byte={p[1]} src_byte={p[2]} len={p[3]}"
              for p in event["parameters"]]
    return "\n".join(lines)


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for spec in sys.argv[2:]:
        name, path = spec.split("=", 1)
        events = pbe.parse(pathlib.Path(path).read_bytes())["events"]
        walls, inits, arena = [], [], []
        for event in events:
            hits = []
            for k, instruction in enumerate(event["instructions"]):
                bank, ident, _, _, args = instruction
                w = words(args)
                if bank in WALL_BANKS or (bank, ident) in {(2004, 2), (3, 6)}:
                    hits.append(line(k, instruction))
                if bank == 2000 and any(7600 <= x <= 7699 for x in w[:3]):
                    inits.append(f"event {event['id']}:{line(k, instruction)}")
            if hits:
                walls.append(f"event {event['id']}:\n" + "\n".join(hits))
            named = any(set(words(i[4])) & ARENA_FLAGS for i in event["instructions"])
            if 13404700 <= event["id"] <= 13404899 or event["id"] in ARENA_FLAGS or named:
                arena.append(event_text(event))
        (out / f"{name}.walls.txt").write_text(
            f"# {path}\n# InitializeEvent of common 7600-7699 (multiplayer walls):\n" +
            ("\n".join(inits) or "(none)") +
            "\n\n# events with 2005:x / 2006:x / 2004:2 / 3:6:\n" + "\n\n".join(walls) + "\n",
            encoding="utf-8")
        (out / f"{name}.arena.txt").write_text(f"# {path}\n" + "\n\n".join(arena) + "\n",
                                               encoding="utf-8")
        print(f"{name}: {len(events)} events, {len(inits)} wall inits, {len(walls)} events with "
              f"object/SFX/3:6, {len(arena)} arena events")


if __name__ == "__main__":
    main()
