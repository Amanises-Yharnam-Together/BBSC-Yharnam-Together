"""Lists m21_00 events 12100110-12100119 as instructions (bank:id, layer, arguments as int32 words
and hex), with their parameter rows, from an event file; uses tools/re/party_boss_events.parse."""
import struct
import sys

sys.path.insert(0, r"C:\bb\release-src\tools\re")
import party_boss_events as pbe  # noqa: E402

WANTED = range(12100110, 12100120)


def listing(path: str) -> str:
    data = open(path, "rb").read()
    parsed = pbe.parse(data)
    lines = [f"# {path}"]
    for event in parsed["events"]:
        if event["id"] not in WANTED:
            continue
        lines.append(f"\nevent {event['id']} rest={event['rest']} "
                     f"({len(event['instructions'])} instructions)")
        for k, (bank, ident, length, layer, args) in enumerate(event["instructions"]):
            words = struct.unpack_from(f"<{len(args) // 4}i", args) if len(args) >= 4 else ()
            layer_text = "" if layer in (-1, 0xFFFFFFFF) else f" layer={layer}"
            lines.append(f"  {k:2d} {bank}:{ident:<4d}{layer_text} args={list(words)} "
                         f"hex={args.hex()}")
        for parameter in event["parameters"]:
            lines.append(f"  param instr={parameter[0]} dst_byte={parameter[1]} "
                         f"src_byte={parameter[2]} len={parameter[3]}")
    found = {e["id"] for e in parsed["events"]} & set(WANTED)
    lines.append(f"\n# events found: {sorted(found)}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("\n\n".join(listing(path) for path in sys.argv[1:]))
