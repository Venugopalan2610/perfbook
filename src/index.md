# Deriving Systems

Your programs print numbers at you all day. A duration in a log line, a
benchmark summary, a p99 on a dashboard you scroll past. How many of
them have you ever checked?

Not measured again. Checked: worked out what the number should have
been, then looked to see whether the one on your screen was anywhere
near it. Hardly anyone does, and it takes about ten seconds.

Here is what those ten seconds buy. Write four kilobytes to a file,
time the call, and it says success in a few microseconds. But a drive
is a small computer at the far end of a bus, and making data survive a
power cut takes it far longer than that: on the book's reference
machine, a hundred microseconds at the very least. Your write came back
long before the fastest durable write could have finished. So it was
not durable. Something you do a thousand times a day just reported success,
and the success was smaller than it sounded.

One division. No profiler, no flame graph, no afternoon gone.

This book is thirteen of them. Nothing is taken on authority: each
chapter opens with a number that does not fit, usually one you predict
and then measure on your own machine, spends a couple of pages on long
division, and ends with one sentence worth remembering.

<div class="start">

[Start here: Success, Too Soon](./01-success-too-soon.md)<br>
Where those four kilobytes actually went.

</div>

---

There is a [preface](./preface.md) if you would rather know what you are
holding first, and an [introduction](./introduction.md) if you want the
method stated plainly before you watch it used. Neither is required, and
the first chapter assumes you skipped both.
