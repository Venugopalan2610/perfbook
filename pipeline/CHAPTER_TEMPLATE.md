# <Title>

> <Epigraph: one line, ideally slightly wry.>

<THE ANOMALY - open with a sentence or two of why the reader should care,
then the measurement that doesn't fit. Never open with a definition. It's
fine to take a short paragraph to set the scene before the number lands
— that's motivation, not stalling.>

## N.1 Candidates and the Ratio

<Name the possibilities. Name the spread between them in the same breath.
If the spread is under 2x, this isn't the chapter's real question.>

<div class="rule" id="kebab-case-id">
<span class="rule-id">Rule N - Short name</span>
One sentence. Napkin-sized. If it needs a comma-spliced second clause,
it's two rules.
</div>

## N.2 The Axioms

<The constants you're handing over. Say plainly that they can't be
derived. Put them in a table.>

## N.3 Doing the Division

<Show the arithmetic in a code block. Then the ruler — add a call to
`ruler(...)` in `pipeline/make_charts.py` with this chapter's values,
regenerate (`pipeline/.venv/bin/python pipeline/make_charts.py`), and
embed the result:>

<img class="ruler-chart" src="img/ruler-NN-slug.svg" alt="Describe what the ruler shows and what the placement proves.">

## N.4 What This Rules Out

<Which candidates the arithmetic sets aside, and why the survivor is the
only one left standing. Turn the floor test on your own answer at least
once per chapter. Curious, not adversarial — we're narrowing things down
together, not prosecuting a wrong guess.>

## N.5 The Pictorial

<If it plots numbers (a roofline, a bar comparison), generate it with
matplotlib in `pipeline/make_charts.py` like the ruler above. If it's a
simple box-and-arrow flow with no axes or scale, ASCII in a code block
is still fine. Either way — this is the thing that gets screenshotted.
Earn it.>

<div class="aside">
Margin notes go here. Use them for the thing you'd say out loud but
wouldn't put in the main line.
</div>

<div class="challenges">

## Challenges

<Four questions. No answers, ever. At least one should be unanswerable
from this chapter alone.>

</div>

<div class="challenges" id="design-note">

## Design Note: <Title>

<The opinionated digression. One idea, argued, not hedged.>

</div>
