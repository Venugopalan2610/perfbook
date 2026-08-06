#!/usr/bin/env python3
"""Regenerate the ladder in src/course.md from vllm-from-scratch's stages.yaml.

The course is a separate repository, and its twenty stages are defined
in exactly one place: `stages.yaml`. That file is what `./vc guide`
reads, so it is the truth. Copying it into prose here by hand would
guarantee the two drift, and the drift would be silent.

So this script owns only the ladder, and only the part of the page
between the two markers:

    <!-- BEGIN LADDER -->  ... generated ...  <!-- END LADDER -->

Everything outside those markers is written by hand and is never
touched. Edit the prose in src/course.md directly.

Unlike make_sitemap.py, **this does not run in CI**, because CI checks
out perfbook alone and cannot see the other repository. The output is
committed. Re-run it when stages.yaml changes:

    ~/vllm-from-scratch/.venv/bin/python pipeline/make_course.py

or point it somewhere else:

    python pipeline/make_course.py --stages /path/to/stages.yaml
"""
import argparse
import pathlib
import re
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "src" / "course.md"
DEFAULT_STAGES = pathlib.Path.home() / "vllm-from-scratch" / "stages.yaml"

BEGIN = "<!-- BEGIN LADDER -->"
END = "<!-- END LADDER -->"

# The same five pips ./vc guide prints in the terminal, so the page and
# the CLI agree about how hard a stage is claimed to be.
def pips(n):
    return "[" + "*" * n + "." * (5 - n) + "]"


def fold(text):
    """YAML folded scalars arrive as one long line. Wrap them so the
    markdown source stays diffable."""
    return "\n".join(textwrap.wrap(" ".join(text.split()), 72))


def render(arcs):
    out = []
    n = 0
    for arc in arcs:
        out.append(f"## {arc['id']} · {arc['name']}\n")
        out.append(fold(arc["blurb"]) + "\n")
        for s in arc["stages"]:
            n += 1
            title = s["name"]
            out.append(
                f'### {n:02d} · {title} '
                f'<span class="stage-diff">{pips(s["difficulty"])}</span>\n'
            )
            out.append(fold(s["insight"]) + "\n")
            out.append(
                '<div class="stage-meta">\n'
                f'<span class="k">Build</span><span><code>{s["file"]}</code> '
                f'{" ".join(s["deliver"].split())}</span>\n'
                f'<span class="k">Gate</span>'
                f'<span>{" ".join(s["measure"].split())}</span>\n'
                "</div>\n"
            )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", type=pathlib.Path, default=DEFAULT_STAGES)
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        sys.exit(
            "PyYAML is not installed in this interpreter. This script is not\n"
            "part of the build, so perfbook has no environment of its own for\n"
            "it. Easiest is to borrow the course's:\n\n"
            "    ~/vllm-from-scratch/.venv/bin/python pipeline/make_course.py\n"
        )

    if not args.stages.exists():
        sys.exit(
            f"no stages.yaml at {args.stages}\n"
            "Clone vllm-from-scratch beside this repo, or pass --stages."
        )

    arcs = yaml.safe_load(args.stages.read_text())["arcs"]
    ladder = render(arcs)

    page = PAGE.read_text()
    if BEGIN not in page or END not in page:
        sys.exit(f"{PAGE} has lost its {BEGIN} / {END} markers.")

    new = re.sub(
        re.escape(BEGIN) + r".*?" + re.escape(END),
        f"{BEGIN}\n\n{ladder}\n{END}",
        page,
        flags=re.DOTALL,
    )

    # The book bans em-dashes in src/. A stage description could smuggle
    # one in from the other repository, so catch it here rather than in
    # review.
    if "—" in ladder:
        sys.exit("an em-dash came through from stages.yaml; fix it there")

    PAGE.write_text(new)
    total = sum(len(a["stages"]) for a in arcs)
    print(f"wrote {PAGE.relative_to(ROOT)}: {len(arcs)} arcs, {total} stages")


if __name__ == "__main__":
    main()
