#!/usr/bin/env python3
"""Check that every .quip will land where it was meant to.

Two failures, both invisible in the markdown and both obvious on the
page, which is the worst combination:

  ANCHOR   A float attaches to the content that comes AFTER it. A quip
           written at the end of a section therefore floats beside the
           NEXT section's heading, not beside the argument it is joking
           about. Put the quip immediately before the paragraph you want
           it beside; it comments on the one above.

  SPACING  .quip sets `clear: right`, so two quips closer together than
           one is tall will stack, and the second drifts away from its
           paragraph. Charts and code blocks count as vertical space
           here: measuring only the prose between two quips reports
           collisions that a figure has already resolved.

Exit code is nonzero if anything needs moving. Run it before committing
marginalia.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUIP = '<p class="quip">'

# A quip sitting before any of these is anchored to the wrong thing.
NOT_PROSE = {
    "a section heading": r"^#{2,}\s",
    "a code fence": r"^```",
    "a chart": r"^<img",
    "a rule box": r'^<div class="rule"',
    "an aside": r'^<div class="aside"',
    "the challenges": r'^<div class="challenges"',
    "a table": r"^\|",
}

# Rendered height of a quip, in the same units `height()` returns: about
# 220px wide and five lines tall, against prose running ~700px wide.
CLEARANCE = 520


def height(segment):
    """Rough rendered height of the material between two quips."""
    prose = re.sub(r"<[^>]+>", "", re.sub(r"<img[^>]*>", "", segment))
    return (len(prose.strip())
            + 900 * len(re.findall(r"<img", segment))
            + 200 * len(re.findall(r"^```", segment, re.M)))


def main():
    problems = []
    total = 0

    for f in sorted((ROOT / "src").glob("[01][0-9]-*.md")):
        text = f.read_text()
        lines = text.split("\n")
        rel = f.name

        seen = [l for l in lines if l.startswith(QUIP)]
        total += len(seen)
        for dup in {q for q in seen if seen.count(q) > 1}:
            problems.append(f"{rel}: appears twice: {dup[:60]}...")

        for i, line in enumerate(lines):
            if not line.startswith(QUIP):
                continue
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            after = lines[j] if j < len(lines) else "<end of file>"
            for what, pattern in NOT_PROSE.items():
                if re.match(pattern, after):
                    problems.append(
                        f"{rel}:{i + 1}: floats beside {what}, not prose. "
                        f"Move it above the paragraph before it.")
                    break

        ends = [m.end() for m in re.finditer(r"<p class=\"quip\">.*?</p>",
                                             text, re.S)]
        starts = [m.start() for m in re.finditer(re.escape(QUIP), text)]
        for a, b in zip(ends, starts[1:]):
            gap = height(text[a:b])
            if gap < CLEARANCE:
                line_no = text[:b].count("\n") + 1
                problems.append(
                    f"{rel}:{line_no}: only {gap} of {CLEARANCE} clearance "
                    f"from the previous quip; they will stack.")

    for p in problems:
        print(f"  {p}")
    print(f"\n{total} quips, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
