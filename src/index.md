# Deriving Systems

Have you ever been handed a number and not known whether to be
impressed? A write comes back in twenty-five microseconds. A GPU runs at
forty percent of its memory bandwidth. An `fsync` spends a hundred
microseconds to persist eight bytes. Every one of those is either
completely ordinary or a serious bug, and telling which is one division
on the back of an envelope.

Nobody teaches the division.

So this is twelve chapters of doing it in front of you. Each one opens
with a measurement that cannot possibly be true, spends a couple of pages
on long division, and ends with one sentence worth remembering. Nothing
is looked up. The whole thing runs on about a dozen constants you already
half know, and a willingness to commit to a number before you check it.

By the end you will have caught a benchmark that was timing an empty
program, worked a CRC by hand to find where a file stops telling the
truth, and gone looking for four and a half milliseconds hiding in the
gaps between two GPU kernels.

<div class="start">

[Start here: Twenty-Five Microseconds](./01-twenty-five-microseconds.md)<br>
A write that returns far too quickly to have happened.

</div>

---

There is a [preface](./preface.md) if you would rather know what you are
holding first, and an [introduction](./introduction.md) if you want the
method stated plainly before you watch it used. Neither is required, and
the first chapter assumes you skipped both.
