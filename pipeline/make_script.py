#!/usr/bin/env python3
"""Turn a chapter into a narration script you can read off a screen.

    pipeline/make_script.py                 # all chapters -> scripts/
    pipeline/make_script.py 07              # just one

The prose is already written to be spoken, so this is mostly adaptation
rather than rewriting. What it actually solves:

  arithmetic   code blocks full of `÷` and `µs` become sentences
  tables       become spoken lists, or get marked SKIP if they are
               reference material nobody wants read at them
  diagrams     ASCII art cannot be read aloud at all, so it gets a
               [DIAGRAM] marker with a suggested line to say instead
  rule boxes   marked, because they are the takeaway and want a gear change
  asides       marked, because they are parenthetical and want a lighter one

Anything in [BRACKETS] is a stage direction. Do not read it.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "scripts"
WPM = 150

# Symbols a reader stumbles over at speed. Expanded so your eye does not
# have to translate mid-sentence.
SPEAK = [
    # singular first: "1 MB" must not become "1 megabytes"
    (r"\b1 KB\b", "one kilobyte"), (r"\b1 MB\b", "one megabyte"),
    (r"\b1 GB\b", "one gigabyte"), (r"\b1 TB\b", "one terabyte"),
    (r"=", " is "),
    (r"÷", " divided by "), (r"×", " times "), (r"≈", " approximately "),
    (r"≤", " at most "), (r"≥", " at least "), (r"→", " gives "),
    (r"->", " gives "), (r"(?<=[\d ])µs\b", " microseconds"), (r"(?<=[\d ])ms\b", " milliseconds"),
    (r"(?<=[\d ])ns\b", " nanoseconds"), (r"\bGB/s\b", " gigabytes per second"),
    (r"\bMB/s\b", " megabytes per second"), (r"\bTB/s\b", " terabytes per second"),
    (r"\bGFLOP/s\b", " gigaflops per second"), (r"\bTFLOP/s\b", " teraflops per second"),
    (r"\bGFLOP\b", " gigaflop"), (r"\bTFLOP\b", " teraflop"),
    (r"\bKB\b", " kilobytes"), (r"\bMB\b", " megabytes"),
    (r"\bGB\b", " gigabytes"), (r"\bTB\b", " terabytes"),
    (r"\bFLOP/byte\b", " flop per byte"),
]


def speakable(s):
    for pat, rep in SPEAK:
        s = re.sub(pat, rep, s)
    return re.sub(r"\s+", " ", s).strip()


def is_diagram(block):
    return len(re.findall(r"[│┌└├─▼▲█╪═^]", block)) > 5


def render_code(block):
    body = block.strip("`\n")
    body = re.sub(r"^\w+\n", "", body)          # drop a language tag
    if is_diagram(body):
        shown = "\n".join("  | " + l for l in body.splitlines()[:14])
        return ("[DIAGRAM. Cannot be read aloud. Describe it in one or two\n"
                "  sentences of your own, then carry on. It looks like this:]\n"
                + shown)
    lines = [speakable(l) for l in body.splitlines() if l.strip()]
    return "[ARITHMETIC. Read it as sentences, at half speed.]\n" + "\n".join(
        "  " + l for l in lines)


def render_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [c for c in cells if not all(set(x) <= set("-: ") for x in c)]
    if not cells:
        return ""
    head, body = cells[0], cells[1:]
    out = ["[TABLE. Read the rows that carry the argument; skip the rest.]"]
    for row in body:
        pairs = ", ".join(f"{h}: {v}" for h, v in zip(head, row) if v)
        out.append("  " + speakable(pairs))
    return "\n".join(out)


def convert(path):
    text = path.read_text()
    out, i = [], 0
    lines = text.splitlines()

    title = lines[0].lstrip("# ").strip()
    words = len(re.sub(r"<[^>]+>", " ", text).split())
    out.append("=" * 66)
    out.append(f"  {title.upper()}")
    out.append(f"  roughly {words / WPM:.0f} minutes at a comfortable pace")
    out.append("=" * 66)
    out.append("")
    out.append("[Anything in brackets is a stage direction. Do not read it.]")
    out.append("[Pause where you see a blank line. Longer at a section break.]")
    out.append("")

    while i < len(lines):
        ln = lines[i]

        if ln.startswith("# "):
            i += 1
            continue
        if ln.startswith("> "):
            out.append("[EPIGRAPH. Slowly, then a real pause.]")
            out.append("  " + ln[2:].strip())
            out.append("")
            i += 1
            continue
        if ln.startswith("## "):
            out.append("")
            out.append(f"[SECTION BREAK. Take a breath.]  {ln.lstrip('# ').strip()}")
            out.append("")
            i += 1
            continue
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append(render_code("\n".join(lines[i:j + 1])))
            out.append("")
            i = j + 1
            continue
        if ln.strip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            t = render_table(lines[i:j])
            if t:
                out.append(t)
                out.append("")
            i = j
            continue
        if "<img" in ln:
            alt = re.search(r'alt="([^"]*)"', ln)
            desc = alt.group(1) if alt else "a chart"
            first = desc.split(". ")[0].strip().rstrip(".")
            out.append("[CHART on the page. Say a one-line version, then move on.")
            out.append(f"  It shows: {first}.]")
            out.append("")
            i += 1
            continue
        if 'class="rule"' in ln:
            j = i
            while j < len(lines) and "</div>" not in lines[j]:
                j += 1
            body = " ".join(lines[i:j + 1])
            rid = re.search(r'rule-id">([^<]*)<', body)
            txt = re.sub(r"<[^>]+>", " ", body)
            txt = txt.replace(rid.group(1) if rid else "", "")
            out.append("[RULE BOX. This is the takeaway. Slow down and land it.]")
            if rid:
                out.append("  " + re.sub(r"\s*·\s*", ", ", rid.group(1)).strip())
            out.append("  " + speakable(txt))
            out.append("")
            i = j + 1
            continue
        if 'class="aside"' in ln:
            j = i
            while j < len(lines) and "</div>" not in lines[j]:
                j += 1
            txt = speakable(re.sub(r"<[^>]+>", " ", " ".join(lines[i:j + 1])))
            if txt.lower().startswith("run it") or txt.lower().startswith("build it"):
                out.append("[ASIDE about running the code. Optional: skip it if")
                out.append(" the audio should stand alone.]")
            else:
                out.append("[ASIDE. Lighter, quicker, like a footnote said out loud.]")
            out.append("  " + txt)
            out.append("")
            i = j + 1
            continue
        if 'class="challenges"' in ln:
            note = 'id="design-note"' in ln
            j = i
            depth = 0
            while j < len(lines):
                depth += lines[j].count("<div") - lines[j].count("</div>")
                if depth == 0 and j > i:
                    break
                j += 1
            block = "\n".join(lines[i:j + 1])
            if note:
                out.append("[DESIGN NOTE. This is the closing argument. Unhurried.]")
                body = re.sub(r"<[^>]+>|^#+ .*$", "", block, flags=re.M)
                for para in [p.strip() for p in body.split("\n\n") if p.strip()]:
                    out.append("  " + speakable(para))
                    out.append("")
            else:
                out.append("[CHALLENGES. Read them if you like, or say:")
                out.append('  "There are four challenges on the page. No answers,')
                out.append('   on purpose." Then stop.]')
                out.append("")
            i = j + 1
            continue
        if ln.startswith("<") or ln.startswith("*PLP"):
            i += 1
            continue

        if ln.strip():
            j = i
            while j < len(lines) and lines[j].strip() and not lines[j].startswith(
                    ("#", ">", "|", "<", "```")):
                j += 1
            para = speakable(" ".join(lines[i:j]))
            para = re.sub(r"\*\*(.+?)\*\*", r"\1", para)
            para = re.sub(r"\*(.+?)\*", r"\1", para)
            para = re.sub(r"`([^`]+)`", r"\1", para)
            para = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", para)
            out.append(para)
            out.append("")
            i = j
            continue
        i += 1

    return "\n".join(out).replace("\n\n\n", "\n\n")


def main():
    OUT.mkdir(exist_ok=True)
    want = sys.argv[1] if len(sys.argv) > 1 else None
    for f in sorted(ROOT.glob("src/[01][0-9]-*.md")):
        if want and not f.name.startswith(want.zfill(2)):
            continue
        dest = OUT / (f.stem + ".txt")
        dest.write_text(convert(f))
        print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
