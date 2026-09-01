## What this changes

<!-- One or two sentences. What is different after this is merged? -->

## Why

<!-- The problem it solves. If it fixes an issue, link it: Fixes #123 -->

## Checklist

- [ ] `pytest tests/` passes in `mcp/vault-mcp`
- [ ] `bash -n` and `shellcheck --severity=warning` pass on any shell script I touched
- [ ] If I touched `vault-template/`: every gotcha still opens with a severity callout, and every
      new folder has an `_INDEX.md`
- [ ] Any claim I added is checkable — no unverified numbers, no unsubstantiated comparisons
- [ ] Docs still say what they mean: I have not softened a deliberate position into vague advice

## Anything reviewers should look at closely

<!-- Optional. A decision you were unsure about, a trade-off you made. -->
