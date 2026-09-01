---
title: "<Conclusion, not topic>"
type: gotcha
tags: [gotcha]
project: ""
severity: warning
date: <YYYY-MM-DD>
---

# <Conclusion, not topic>

> [!warning] <Short title>
> <One sentence: the problem and its consequence.>

<!--
  Choose the severity:
    danger  — data loss, production breakage, silent corruption
    warning — the standard trap: costs an hour, no lasting damage
    tip     — a better way that is not obvious
    info    — context that prevents a wrong assumption

  THE CALLOUT IS MANDATORY. Without it this note is invisible to gotcha retrieval.
  Keep the callout body to one sentence — it is what gets surfaced as a warning.
-->

## Problem

What is the unexpected behaviour? Describe the symptom as you would first meet it, not as you
understand it afterwards — that is how it will be searched for.

## Cause

Why does it happen? One paragraph. This is the part that makes the fix memorable.

## Fix

```bash
# the correct approach
```

## Prevention

What makes this not happen again — a convention, a lint rule, a guard in code.

## Navigation

- [[GLOBAL/gotchas/_INDEX|Global gotchas]]
