# Contributing

Thanks for considering a contribution. This is a template people copy and adapt, which shapes what
is useful here: **changes that make the conventions clearer or the runnable parts more reliable**.

## What is in scope

- Fixes to the runnable parts — `bootstrap.sh`, the hooks, the reference MCP server.
- Corrections where the docs are wrong, unclear, or contradict themselves.
- New anti-patterns and failure modes, **if you have actually hit them**. A failure mode with a
  concrete symptom and a fix is worth more than any amount of general advice.
- Portability fixes: this was built on WSL2 + Ubuntu; macOS and native Linux reports are welcome.

## What is out of scope

- A longer `CLAUDE.md` template. Its shortness is the point — see [docs/03-claude-md.md](docs/03-claude-md.md).
- Features for the reference MCP server that are not needed to demonstrate a pattern. It is a
  teaching implementation, not a product. Embeddings, a graph API, and file watching were all left
  out on purpose.
- Company- or vendor-specific content. Everything here has to stay generic.

## Ground rules

**Keep the docs opinionated.** These files take positions — "facts never go in `CLAUDE.md`",
"symlink, never copy", "the callout is mandatory". If you disagree with one, open an issue and
argue the case; do not soften it into advice that helps nobody.

**Every claim has to be checkable.** No unverified numbers, no comparisons to other projects that
cannot be substantiated. If you state that something fails, say how to reproduce it.

**Comments explain WHY.** The code shows what. See the comment rules the template itself teaches.

## Before opening a pull request

```bash
make check          # runs everything CI runs
```

Or by hand:

```bash
# tests
cd mcp/vault-mcp && pytest tests/ -v

# shell scripts
find . -name '*.sh' -exec bash -n {} \;
shellcheck --severity=warning $(find . -name '*.sh')

# documentation links, and the vault template's own health check
python3 .github/scripts/check-links.py
python3 .github/scripts/check-vault.py
```

`make check` runs exactly what CI runs, so a green one predicts the other. CI additionally
performs an end-to-end `bootstrap.sh` run on every pull request.

If you touch the vault template, remember the rule it teaches: **a gotcha without a severity
callout is invisible to retrieval.** CI will fail on it, which is the point.

## Commit messages

Present tense, imperative, and specific about what changed. The body explains why, if that is not
obvious from the diff.

## Licence

By contributing you agree that your work is published under the [MIT Licence](LICENSE).
