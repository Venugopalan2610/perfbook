# Pipeline

Four stages. Stage 4 is the one that matters.

## 1 - Dump
Paste the raw conversation into `raw/NN-topic.md`. No editing. Do this the
same day: the questions you asked are the outline, and you will forget
their order faster than you expect.

## 2 - Extract
Pull out, in this order:
- the anomaly (the number that didn't fit)
- every ratio that killed a candidate
- any diagram that plots numbers (rulers, roofline-style charts, bar
  comparisons) — these get generated with matplotlib, not hand-drawn.
  See "Charts" below. ASCII is still fine for simple box-and-arrow flow
  diagrams (a pipeline, a ladder of layers) — nothing with axes or scale.
- the rules, as single sentences
- every question that was asked but not answered

## 3 - Draft
`CHAPTER_TEMPLATE.md` into prose. Cut the false starts. Cut the
corrections. A chapter is not a transcript; it is the argument the
transcript was groping toward.

## 4 - Your rewrite pass. NON-SKIPPABLE.
Rewrite every rule box in your own words without looking at the draft.
If you can't, you didn't learn it, and publishing it will feel like
progress while producing none.

## Charts
Any diagram that plots real numbers on an axis — a magnitude ruler, a
roofline chart, a memory-budget bar — is generated with matplotlib in
`pipeline/make_charts.py`, not hand-positioned in CSS or drawn in ASCII.
Both of those were tried first and both rot: CSS percentage-positioning
drifts out of alignment the moment font sizes change, and ASCII
box-drawing breaks the instant a label is a character longer than you
budgeted for. A real plotting library gets the arithmetic right by
construction.

```
python3 -m venv pipeline/.venv          # once
pipeline/.venv/bin/pip install matplotlib
pipeline/.venv/bin/python pipeline/make_charts.py
```

Output lands in `src/img/*.svg`, which mdBook copies to the built site
automatically. Add a new chart by adding a function call at the bottom
of `make_charts.py`, using the palette constants already defined there
(pulled from `theme/custom.css` — keep them in sync if the palette
changes). Reference the result from a chapter with a plain `<img>` tag,
classed `ruler-chart` or `chart` (styled in `theme/custom.css`).

## Invariants
- Rule anchors (`id="floor-test"`) are permanent. Never rename one. The
  Rules Index links to them, and so will your memory.
- Challenges never get answers. Not later, not in an appendix.
- One chapter, one anomaly. Two numbers that don't fit means two chapters.
