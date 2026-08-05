#!/usr/bin/env python3
"""Voice check for the Feynman rewrite.

The old we:you ratio band is retired: it enforced a third-person-plural
voice the book no longer wants. What we check now is that the person is
present and the jargon is earned.
"""
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parent.parent / "src"
CHAPTERS = sorted(SRC.glob("[01][0-9]-*.md"))

# Terms that must not land before the reader has a reason to care.
JARGON = ["arithmetic intensity", "roofline", "ridge point", "write-ahead",
          "copy-on-write", "rejection sampling", "iteration-level"]

fail = 0
earned = set()   # jargon introduced by an earlier chapter is fair game later
print(f"{'chapter':<34} {'I':>3} {'you':>4} {'we':>4}  {'1st ¶':>6}  jargon")
for f in CHAPTERS:
    text = f.read_text()
    body = text.split('<div class="challenges">')[0]
    i = len(re.findall(r"\bI\b", body))
    you = len(re.findall(r"\b(you|your|you're|you've)\b", body, re.I))
    we = len(re.findall(r"\b(we|our|us|we're|we've|let's)\b", body, re.I))

    # First paragraph after the epigraph should be concrete, not a definition.
    paras = [p for p in body.split("\n\n") if p.strip()
             and not p.startswith(("#", ">", "|", "<"))]
    first = paras[0] if paras else ""
    early_jargon = [j for j in JARGON
                    if j in first.lower() and j not in earned]

    problems = []
    if i < 1:
        problems.append("no first person")
    if you < 5:
        problems.append("reader absent")
    if early_jargon:
        problems.append("jargon in ¶1: " + ", ".join(early_jargon))
    status = "ok" if not problems else "; ".join(problems)
    if problems:
        fail += 1
    # anything this chapter used anywhere is earned for the ones after it
    earned.update(j for j in JARGON if j in text.lower())
    print(f"{f.name:<34} {i:>3} {you:>4} {we:>4}  {len(first.split()):>6}  {status}")

print()
if fail:
    print(f"{fail} chapter(s) need work")
    sys.exit(1)
print("voice: ok")
