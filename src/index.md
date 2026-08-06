# Deriving Systems

Your programs print numbers at you all day. A duration in a log line, a
benchmark summary, a p99 on a dashboard you scroll past. How many of
them have you ever checked?

Not measured again. Checked: worked out what the number should have
been, then looked to see whether the one on your screen was anywhere
near it. Hardly anyone does, and it takes about ten seconds.

Here is what those ten seconds buy. Write a megabyte to a file, time the
call, and it comes back in twenty-five microseconds. But a megabyte
cannot cross a memory bus that quickly. At ten gigabytes a second it
takes a hundred microseconds to move, and that is the floor for the
fastest thing that could possibly have happened. Twenty-five is under
the floor. So the work did not happen. Something you have done a
thousand times just reported success, and it was not telling you the
truth.

One division. No profiler, no flame graph, no afternoon gone.

This book is twelve of them. Nothing is looked up: each chapter opens
with a measurement that cannot be true, spends a couple of pages on long
division, and ends with one sentence worth remembering.

<div class="start">

[Start here: Twenty-Five Microseconds](./01-twenty-five-microseconds.md)<br>
Where that megabyte actually went.

</div>

---

There is a [preface](./preface.md) if you would rather know what you are
holding first, and an [introduction](./introduction.md) if you want the
method stated plainly before you watch it used. Neither is required, and
the first chapter assumes you skipped both.
