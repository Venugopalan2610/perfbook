#!/usr/bin/env python3
"""Generate src/sitemap.xml from SUMMARY.md.

mdBook has no sitemap of its own, and a new domain with no inbound links
has no other way to tell a crawler what pages exist. Driven off
SUMMARY.md so it cannot drift from the actual book.
"""
import datetime
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://derivingsystems.com"
today = datetime.date.today().isoformat()

summary = (ROOT / "src" / "SUMMARY.md").read_text()
pages = ["index.html"] + [
    m.group(1).replace(".md", ".html")
    for m in re.finditer(r"\]\(\./([\w-]+\.md)\)", summary)
    if m.group(1) != "index.md"
]

seen, urls = set(), []
for p in pages:
    if p in seen:
        continue
    seen.add(p)
    loc = f"{BASE}/" if p == "index.html" else f"{BASE}/{p}"
    prio = "1.0" if p == "index.html" else "0.8"
    urls.append(
        f"  <url>\n    <loc>{loc}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <priority>{prio}</priority>\n  </url>"
    )

out = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
       + "\n".join(urls) + "\n</urlset>\n")
(ROOT / "src" / "sitemap.xml").write_text(out)
print(f"wrote src/sitemap.xml with {len(urls)} urls")
