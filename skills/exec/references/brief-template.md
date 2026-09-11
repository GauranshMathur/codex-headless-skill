# Writing a brief codex executes instead of wanders on

## The template

```
## Goal
<one sentence; an outcome, not a method>

## Context
- <where the relevant code lives>
- <conventions that apply>
- <what has already been tried and failed>

## Files you will likely touch
- <path> — <what changes>

## Definition of done
<the exact command that must pass>

## Out of scope
- <what not to touch>
```

## A brief that wanders

> Clean up the S3 client, it's getting messy. Add retries too.

Everything is wrong here: "clean up" has no observable outcome, two unrelated
asks share one run, no file is named so codex explores for ten minutes, there is
no command that decides whether it worked, and with nothing out of scope it will
happily refactor three neighbouring modules on the way past.

## The same task, briefed well

> ## Goal
> `S3Client.get_object` retries transient failures instead of raising on the
> first one.
>
> ## Context
> - The client is `src/storage/s3_client.py`; it wraps boto3 directly.
> - Retry helpers already exist in `src/util/retry.py` — use `with_backoff`
>   rather than writing a new one.
> - `tenacity` is not a dependency and must not become one.
>
> ## Files you will likely touch
> - `src/storage/s3_client.py` — wrap the boto3 call
> - `tests/test_s3_client.py` — add coverage for the retry path
>
> ## Definition of done
> `pytest tests/test_s3_client.py -q` passes.
>
> ## Out of scope
> - The upload path. Only `get_object`.
> - Do not change `S3Client`'s public signature.

## Why each section earns its place

**Goal** as an outcome, not a method, leaves codex free to find a better
implementation than the one you had in mind — while still being checkable.

**Context** is where you spend the reading you did in step 1. "This helper
already exists" prevents a duplicate; "this has been tried and failed" prevents a
repeat.

**Files** save exploration time and make an over-broad change visible: if codex
touches twenty files when you named two, the brief was wrong.

**Definition of done** is the single highest-value line. Without a command, codex
invents its own idea of finished, and you have no way to disagree.

**Out of scope** is what stops opportunistic refactoring. Codex is agreeable; if
you do not say "not the upload path", the upload path is fair game.

## Repair briefs

When re-prompting a thread after a failure, four lines beat a fresh explanation:

```
What I ran:      pytest tests/test_s3_client.py -q
What I saw:      E   AssertionError: expected 3 calls, got 1
What I expected: the retry wraps get_object, so a transient failure retries twice
Do not change:   the public signature, or anything under src/util/
```

Codex still has its own context from the first attempt, so repeating the original
brief wastes tokens and invites it to redo work that was already correct.
