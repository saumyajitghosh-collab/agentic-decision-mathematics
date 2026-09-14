#!/usr/bin/env python3
"""Repair corruptions in app.js (line-based, base64 payloads)."""
import base64
import subprocess
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "docs/static/js/app.js"

# (line_number_1indexed, sanity_fragment_in_broken_line, b64_of_correct_line)
FIXES = [
    (9, '"&#39;" }[c]',
     'ICBjb25zdCBlc2MgPSAocykgPT4gU3RyaW5nKHMgPz8gIiIpLnJlcGxhY2UoL1smPD4iJ10vZywgKGMpID0+ICh7ICImIjogIiZhbXA7IiwgIjwiOiAiJmx0OyIsICI+IjogIiZndDsiLCAnIic6ICImcXVvdDsiLCAiJyI6ICImIzM5OyIgfVtjXSkpOw=='),
    (165, 'Control layer',
     'ICAgICAgWyJDb250cm9sIGxheWVyIiwgIkF1dG9ub215IiwgU3RyaW5nLnJhd2BcZWxsPVxiaWd3ZWRnZV9rIFxtYXRocm17Y2FwfV9rYCwgImZyb250aWVyIl0s'),
    (335, 'Calibration for this class',
     'ICAgICAgICAgICAgICAgIENhbGlicmF0aW9uIGZvciB0aGlzIGNsYXNzIGF0IM6xPSR7bnVtKGQuY2FsaWJyYXRpb24uYWxwaGEsIDQpfTogJHtlc2MoZC5jYWxpYnJhdGlvbi5yZWFzb24pfS4gRHJpZnQ6ICR7ZC5kcmlmdC5zdGFibGUgPyAic3RhYmxlIiA6IGBtYXRlcmlhbCAoV+KCgSAke2QuZHJpZnQudzF9LCBLTCAke2QuZHJpZnQua2x9JHtkLmRyaWZ0LmN1c3VtX2FsYXJtID8gIiwgQ1VTVU0gYWxhcm0iIDogIiJ9KWB9LjwvcD4='),
    (462, 'mathrm{Score}',
     'ICAgICAgICAgICAgJHtlcShTdHJpbmcucmF3YFxtYXRocm17U2NvcmV9KGEpPVxtYXRocm17QmVuZWZpdH0tMi4wXCxSLTAuNTVcLFxtYXRocm17SXJyZXZ9LTAuNjBcLFVgKX0='),
    (650, 'min',
     'ICAgICAgICAgICR7ZXEoU3RyaW5nLnJhd2BcbWluXHN1bV97aix0fUhDX3tqdH0rMS4xXHN1bV90IEZfdFxxdWFkXHRleHR7cy50Ln1ccXVhZCA0MjBcLEhDX3tqdH0rMC44XCx5X3tqdH1cZ2UgMS4yNVwsV197anR9LFw7XDtcc3VtX2ogeV97anR9XGxlIDQyMFwsRl90LFw7XDsgSENfe2p0fVxnZSBcdW5kZXJsaW5le0hDfV9qLFw7XDsgSEMsRlxpblxtYXRoYmJ7Wn1fK2ApfQ=='),
    (698, 'mathbf{O}',
     'ICAgICAgICAgICR7ZXEoU3RyaW5nLnJhd2BcbWF0aGJme099XCxccHNpIFx0ZXh0eyBhdCB9IGkgXGlmZiBcZXhpc3RzIGpcbGUgaTpccHNpIFx0ZXh0eyBhdCB9IGosXHFxdWFkIFxtYXRoYmZ7R31cLFx2YXJwaGkgXGlmZiBcZm9yYWxsIGk6XHZhcnBoaSBcdGV4dHsgYXQgfSBpYCwgIlBhc3QtdGltZSBMVEwgZXZhbHVhdGVkIG92ZXIgZWFjaCBwcm9wb3NhbCdzIGZpbml0ZSBldmVudCB0cmFjZS4iKX0='),
]

BLOCK_B64 = ('ICAgIHNlbnNpdGl2aXR5OiBbdmlld1NlbnNpdGl2aXR5LCB3aXJlU2Vuc2l0aXZpdHldLAogICAgc2F2aW5nczogW3ZpZXdTYXZpbmdzLCB3aXJlU2F2aW5nc10sCiAgICBwcm9vZjogW3ZpZXdQcm9vZiwgd2lyZVByb29mXSwKICB9OwoKICBmdW5jdGlvbiByb3V0ZSgpIHsKICAgIGNvbnN0IG5hbWUgPSAobG9jYXRpb24uaGFzaCB8fCAiI292ZXJ2aWV3Iikuc2xpY2UoMSk7CiAgICBjb25zdCBrZXkgPSBTQ1JFRU5TW25hbWVdID8gbmFtZSA6ICJvdmVydmlldyI7CiAgICAkJCgiLm5hdiBhIikuZm9yRWFjaCgoYSkgPT4gYS5zZXRBdHRyaWJ1dGUoImFyaWEtY3VycmVudCIsIGEuZGF0YXNldC5zY3JlZW4gPT09IGtleSA/ICJwYWdlIiA6ICJmYWxzZSIpKTsKICAgIGNvbnN0IG1haW4gPSAkKCIjbWFpbiIpOwogICAgY29uc3QgW3ZpZXcsIHdpcmVdID0gU0NSRUVOU1trZXldOwogICAgbWFpbi5pbm5lckhUTUwgPSB2aWV3KCk7CiAgICByZW5kZXJNYXRoKG1haW4pOwogICAgaWYgKHdpcmUpIHdpcmUobWFpbik7CiAgICB3aW5kb3cuc2Nyb2xsVG8oMCwgMCk7CiAgfQoKICBhc3luYyBmdW5jdGlvbiBib290KCkgewogICAgY29uc3QgbWFpbiA9ICQoIiNtYWluIik7CiAgICBtYWluLmlubmVySFRNTCA9IGA8ZGl2IGNsYXNzPSJsb2FkaW5nIj5Mb2FkaW5nIGNhdGFsb2d1ZeKApjwvZGl2PmA7')


def main():
    with open(PATH, "r", encoding="utf-8", errors="surrogateescape") as f:
        content = f.read()
    lines = content.split("\n")
    print(f"Read {len(lines)} lines from {PATH}")

    # --- Check if already fixed (skip if so) ---
    already_fixed = all(
        base64.b64decode(b).decode("utf-8") in content
        for _, _, b in FIXES
    )
    if already_fixed:
        print("File already fixed \u2014 skipping")
        return

    # --- sanity + individual line fixes ---
    for num, frag, b64 in FIXES:
        idx = num - 1
        if idx >= len(lines):
            print(f"FAIL: line {num} out of range")
            sys.exit(1)
        if frag not in lines[idx]:
            # Maybe already fixed on this line
            correct = base64.b64decode(b64).decode("utf-8")
            if lines[idx].strip() == correct.strip():
                print(f"Line {num} already correct \u2014 skipping")
                continue
            print(f"FAIL: line {num} missing fragment {frag!r}: {lines[idx][:100]!r}")
            sys.exit(1)
        lines[idx] = base64.b64decode(b64).decode("utf-8")
        print(f"Fixed line {num}")

    # --- garbage block: replace garbage lines with 20 correct lines ---
    marker = "sensitivity: [viewSensitivity"
    gi = None
    for i, ln in enumerate(lines):
        if marker in ln:
            gi = i
            break
    if gi is None:
        print("No garbage block marker found \u2014 possibly already fixed")
    else:
        end = None
        for j in range(gi + 1, min(gi + 10, len(lines))):
            if "try {" in lines[j]:
                end = j
                break
        if end is None:
            print("End of garbage block not found \u2014 possibly already fixed")
        else:
            if len(lines[gi]) < 60 and "wireSensitivity]" in lines[gi]:
                print("Garbage block already fixed \u2014 skipping")
            else:
                block_lines = base64.b64decode(BLOCK_B64).decode("utf-8").split("\n")
                lines = lines[:gi] + block_lines + lines[end:]
                print(f"Replaced garbage block at line {gi+1}..{end} with {len(block_lines)} correct lines")

    out = "\n".join(lines)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(out)

    # --- verify ---
    r = subprocess.run(["node", "--check", PATH], capture_output=True, text=True)
    if r.returncode != 0:
        print("SYNTAX ERROR AFTER FIX:\n" + r.stderr[:600])
        sys.exit(1)
    print("VERIFIED: app.js syntax OK")


if __name__ == "__main__":
    main()
