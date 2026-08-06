# Deriving Systems — project context

An mdBook that turns Socratic performance-engineering conversations into a
Crafting Interpreters-style reference site. Built for **revision by
retrieval**, not rereading.

## Commands

```
mdbook serve --open     # local, live reload
mdbook build            # outputs to book/ (gitignored)
```

Deploy is automatic: push to `master` (the repo's default branch),
`.github/workflows/mdbook.yml` builds and publishes to GitHub Pages.
Repo Settings → Pages → Source must be set to **GitHub Actions**. The
workflow's `branches:` list has to match the branch name, or nothing
runs and nothing says why.

⚠ **If a deploy hangs in `deployment_queued`, do not "Re-run failed
jobs". It cannot work.** `actions/deploy-pages` cancels its own
deployment when it times out, and a Pages deployment's id *is the
commit SHA*. A re-run recreates the same id, finds it already
cancelled, and fails in about ten seconds with `Deployment cancelled.`
The only way out is a new commit.

Then find out **which** stall you have, because two different failures
look identical from the run list:

```
gh run view --job=<deploy job id> --log \
  | grep -oE "Current status: [a-z_]+" | sort | uniq -c
```

`deployment_queued` means Pages never picked the deployment up, and a
longer timeout cannot help. `deployment_in_progress` means it is working
and the action's 10-minute default is too short, which is what the
`timeout: 1800000` in the workflow is for. On 2026-08-06 it was the
first for about an hour and then became the second, so do not assume it
is the same one you saw last time.

Before blaming the book, check the inputs, because they are cheap to
check and have never yet been the cause: the uploaded artifact should
unpack to a well-formed `artifact.tar` (`gh api
repos/:owner/:repo/actions/artifacts/<id>/zip`), `src/CNAME` must match
the configured domain exactly, and
`gh api repos/:owner/:repo/pages/deployments/<sha>/status` returning 404
means the Pages service never registered the deployment at all, which is
GitHub's side rather than ours.

Live at **https://derivingsystems.com** (the github.io URL 301-redirects
there).

`src/CNAME` is what keeps that custom domain attached. The Pages config
also records it, but this deploy replaces the whole published site on
every run, so the file in `src/` is the durable half. Do not delete it.

`src/robots.txt` and `src/sitemap.xml` exist because a new domain with
no inbound links has no other way to be discovered. The sitemap is
generated from `SUMMARY.md` by `pipeline/make_sitemap.py`, which CI runs
before every build, so adding a chapter updates it automatically.

## Status

- `src/01-five-microseconds.md` through `src/12-spending-the-idle.md` —
  all **written**. Chapter 1 is the reference implementation of both
  format and voice; match it.
- **Voice conversion is complete.** All twelve chapters are in the
  Feynman voice described below. `pipeline/voicecheck.py` exits zero;
  run it before committing prose.
- `src/index.md` is the landing page, `src/preface.md` is about the book
  (origin, the no-lookups rule, how to revise, what it is not) and
  `src/introduction.md` is about the subject (the method itself). They
  are SUMMARY prefix chapters, before the first `---`.
- `src/rules.md` — the Rules Index. The most important page in the book.
- `src/challenges.md` — every question, no answers.
- `src/course.md` — Part V. The map of
  [vllm-from-scratch](https://github.com/Venugopalan2610/vllm-from-scratch),
  which stays a separate repository. **The ladder section is generated**,
  by `pipeline/make_course.py`, from that repo's `stages.yaml`. Only the
  text between `<!-- BEGIN LADDER -->` and `<!-- END LADDER -->` is
  written by the script; the prose around it is by hand. Unlike
  `make_sitemap.py` this does **not** run in CI, because CI checks out
  perfbook alone and cannot see the other repo, so the output is
  committed and you re-run it by hand when stages change:

  ```
  ~/vllm-from-scratch/.venv/bin/python pipeline/make_course.py
  ```

  It needs PyYAML, which is why it borrows the course's virtualenv.
  Twenty stage guides as twenty chapters was considered and rejected: a
  stage is an exercise, not an anomaly, so it would violate invariant 3
  and double the book with material in a different voice.

## The format

Each chapter: **anomaly → candidates and their ratio → the axioms →
the arithmetic → what it rules out → pictorial → rules → challenges →
design note.** See `pipeline/CHAPTER_TEMPLATE.md`.

### ⚠ Editing `theme/custom.css`: 1rem = 10px

mdBook sets the root font-size to 62.5%, so **every `rem` in this
project is a tenth of a pixel value**: `1.9rem` is 19px, `70rem` is
700px. This is easy to forget and fails silently — it once shipped a
400px-wide column of 12.5px text that looked, correctly, "weird." When
adding a size, write the px you want and move the decimal one place.
Verify by measuring rendered `getComputedStyle` values in the browser,
not by eye.

Two custom HTML components, defined in `theme/custom.css`:

- `.rule` — a boxed single-sentence takeaway with a permanent anchor id.
- `.quip` — a wry one-liner that moves into the right margin when there
  is room, and falls back inline when there is not. This is the second
  attempt at marginalia; the first was reverted. See the long comment in
  `custom.css` before touching it. Two things keep it safe: it uses a
  **container query**, not a viewport media query, because the sidebar
  eats ~300px of viewport that a media query cannot see; and the
  threshold is derived from the geometry rather than guessed, because
  `main` is centred so the surplus is halved. Nothing in a `.quip` is
  load-bearing: it is a joke, and it is allowed to be missed.
- `.stage-diff` and `.stage-meta` — `src/course.md` only, and **emitted
  by `pipeline/make_course.py`**, so renaming either class means editing
  the script too.
- `.aside` — margin note, rendered inline at every viewport width.
  (It used to float into the right margin above 1500px via a
  hardcoded negative margin; that clipped off-screen at real-world
  viewport/zoom combinations, so it's inline-only now. Don't
  reintroduce the float without a way to actually verify it across
  viewport sizes — see the comment in custom.css.)

Each chapter opens with a **spot illustration**: `<img
class="chapter-illustration">` sitting between the epigraph and the
first paragraph. These are drawings, not diagrams, and they are
deliberately narrower than the reading column so they do not read as
figures. Generated with FLUX.1-schnell in `~/illustrations`; the
subjects, the art-direction rules and the picked seed per chapter are
recorded there in `subjects.py`, `picks.md` and `assemble.py`.

Note that the drop cap in `theme/custom.css` targets `blockquote + p`,
and the illustration sits between those two, so there is a second
selector for `.chapter-illustration + p`. Move the picture and the drop
cap silently stops rendering.

Any diagram that plots numbers — the ruler (the signature: a log-scale
strip placing a measurement against the candidates it must beat, one
per chapter max), a roofline chart, a memory-budget bar — is a
matplotlib SVG generated by `pipeline/make_charts.py`, embedded with
`<img class="ruler-chart">` or `<img class="chart">`. Not hand-built
HTML/CSS, not ASCII. See `pipeline/README.md`'s Charts section before
adding a new one.

### ⚠ `theme/index.hbs` is a fork

The site-wide footer ("Venugopalan Iyengar · © 2026")
needs a template override, because mdBook has no footer config. So
`theme/index.hbs` is a **verbatim copy of mdBook 0.4.52's default
template** with one `<footer class="book-footer">` block added just
after `{{{ content }}}`.

That means it does not pick up template fixes from newer mdBook
releases. On upgrade:

```
mdbook init --theme /tmp/probe     # get the new default
diff /tmp/probe/theme/index.hbs theme/index.hbs
```

and re-apply the footer block to the new template rather than keeping
the old one. The version this was forked from is recorded here and in
a comment in `theme/custom.css`. The CI workflow pins the same 0.4.52,
so a local upgrade that skips this step will diverge from the deploy.

## Invariants (do not violate)

1. **Rule anchor ids are permanent.** `#floor-test` never gets renamed.
   `src/rules.md` links to them and so does the author's memory.
2. **Challenges never get answers.** Not later, not in an appendix.
3. **One chapter, one anomaly.** Two numbers that don't fit means two
   chapters.
4. **No sub-item anchors in `SUMMARY.md`.** mdBook treats
   `file.md#anchor` as a separate chapter and will clobber the real
   output file. Learned the hard way.
5. Chapters are arguments delivered as talks. Digression is a
   teaching device and stays. Cut genuine false starts and corrections,
   keep the detours that illuminate.

## Voice

Feynman, giving a lecture. Not Feynman-flavoured folksiness: the actual
rhetorical machinery he used, which is a specific and learnable thing.

Read a few pages of *The Character of Physical Law* or the red
Lectures if the voice has drifted. The failure mode to watch for is
**folksy without rigour**: the warmth is only earned if the arithmetic
underneath it is exact.

- **First person, freely.** "I want to show you." "I thought exactly
  that, the first time." The confession is load-bearing: admitting you
  found something confusing is how you earn the right to walk someone
  through it. The book used to prohibit "I" entirely. That was wrong.
- **Second person, constantly.** "You see," "work it out," "if you
  measure this yourself." The reader is in the room. "We" is still fine
  for genuinely shared reasoning ("let's count", "we have two
  possibilities"), so all three persons are in play and no ratio is
  policed. Use whichever one is true in the sentence.
- **Digression is a teaching mechanism, not a failure.** This is the
  point of the whole style. A tangent that appears to wander off and
  then turns out to *be* the argument teaches better than a straight
  line, because the reader arrives at the idea instead of being handed
  it. Digress in the main text, not only in asides. Cut genuine dead
  ends; keep the detours that illuminate.
- **Concrete before abstract, always.** A physical picture, a number
  you can hold, a thing on a desk. The formalism comes after, and only
  if it earns its place.
- **Refuse jargon until it is earned.** When a term finally arrives,
  name it plainly and say why it is called that. "That ratio has a
  name, arithmetic intensity, and it is the only number this chapter
  needs."
- **Short sentences after a long build.** Let the punchline be four
  words. "It is not a mistake."
- **Rhetorical question, then answer it.** Do not leave questions
  hanging for effect.
- **Delight.** It is allowed to find this stuff wonderful, and saying
  so is not unserious.
- **The arithmetic decides, not the authority.** Nobody is right
  because they are senior. If it disagrees with the measurement, it is
  wrong.
- **Repetition for emphasis is fine.** Spoken rhythm. Say the important
  thing twice if twice is what it takes.
- **Humour via analogy and self-deprecation**, never at the reader's
  expense. Still true, still the rule.
- **Prose over bullets** in the chapter body. Bullets are for reference
  material (axiom tables, the Rules Index), not for the argument.
- **No em-dashes (—) anywhere in `src/` or in chart captions.** Use a
  colon when the clause explains, a period when it is a new thought,
  parentheses for a true aside, a comma otherwise. En-dashes in numeric
  ranges (`1–5 ns`, `5–10 ms`) are fine. Check with
  `grep -c '—' src/*.md pipeline/make_charts.py` before committing.

### The voice check

The old we:you ratio band (1.5 to 7) is **retired**. It enforced a
third-person-plural voice that this book no longer wants, and Feynman
inverts it by construction. Replaced with:

```
pipeline/voicecheck.py        # first person present, jargon not front-loaded
```

## Remaining raw material

Chapters 2–8 come from one conversation. The chain, in order:

- **02 The Ladder** — userspace buffer → page cache → drive cache →
  flash. What kills you at each level. `write()` leaves userspace;
  `fsync()` leaves the kernel.
- **03 The Barrier** — fsync costs ~100 µs (NVMe) to ~10 ms (spinning).
  Durability is bought at boundaries, not sprayed everywhere. Ordering
  matters more than durability alone.
- **04 Write-Ahead** — fsync failure is **not retryable**: the kernel
  marks failed pages clean and drops the error (Linux fsync-gate,
  `errseq_t` fix in 4.13). So: write WAL → fsync WAL → **ack** → write
  data pages lazily. The ack is the only line that matters. Also
  `full_page_writes` and why the copy comes from the buffer pool, never
  from the file being protected.
- **05 Group Commit** — fixed batch counts break at low load (1000-event
  batch = 100 s latency at 10 events/sec). Replace with: when an fsync
  completes, start the next covering everyone who arrived while it was in
  flight. Self-tuning. Add a ~200 µs floor to cap flush wear.
- **06 Where the Truth Stops** — torn writes are the *normal* ending of
  every crash. CRC per record finds the edge of the truth. GF(2) long
  division worked by hand. Seed the register nonzero so all-zeros fails.
- **07 The Ridge** — 7B fp16 decode, batch 1: 14 GB weights read,
  14 GFLOP compute → **1 FLOP/byte**. A100 ridge is ~156. 7 ms memory vs
  45 µs compute: the GPU is 99.4% idle. Batching is the same amortization
  trick as group commit.
- **08 The Cache That Ate the Batch** — KV cache is 512 KB/token for a
  7B; 1 GB per 2048-token sequence. 80 GB A100 − 14 GB weights = ~64
  sequences, not the 156 the ridge wants. Memory, not padding, is the
  wall. This is why GQA/MQA/PagedAttention/KV-quant exist.

## Parked

The prefill derivation (2048-token prompt, matrix-matrix instead of
matrix-vector, arithmetic intensity flips to compute-bound) was started
and never finished. It belongs in chapter 7.
