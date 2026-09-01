---
name: <skill-name>
description: >
  <What it does, in one or two concrete sentences — mechanism, not marketing.>
  Trigger on "/<skill-name>", "<literal phrase a user says>", "<another one>".
  Do NOT trigger for <adjacent case> (that is `<other-skill>`) or <another adjacent case>.
argument-hint: "[<arg>]"
allowed-tools: <narrow the tools this skill may use>
---

# <Skill name>

## When this runs

The situation this is for, and the situations it is deliberately not for.

## Preconditions

What must be true. If a precondition is missing, say so and stop — do not improvise around it.

## Steps

1. …
2. …

## Guardrails

- <Never do X.>  ← state guardrails IN the skill, not only in CLAUDE.md: a loaded skill is what
  the model is looking at.

## Write-back

What durable knowledge this skill should put into the knowledge base when it discovers something.
