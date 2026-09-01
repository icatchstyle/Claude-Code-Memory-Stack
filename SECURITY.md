# Security policy

## Scope

This repository contains documentation, shell scripts, and a small MCP server intended to run
**locally, against your own files**. It is not a hosted service and processes no third-party data.

## Reporting a vulnerability

Report suspected vulnerabilities through
[GitHub's private vulnerability reporting](https://github.com/icatchstyle/Claude-Code-Memory-Stack/security/advisories/new).
Please do not open a public issue for anything exploitable.

Expect an initial response within a few days. This is a spare-time project, so please be patient
and, if the issue is urgent for you, say so.

## What is worth reporting

- Path traversal or any other way to make the reference server read or write outside its vault.
- A `bootstrap.sh` path that destroys existing files. It is written never to overwrite; a case
  where it does is a bug worth reporting.
- Anything in the docs that would lead someone to expose a credential.

## Known and accepted design decisions

These are deliberate, not oversights:

- **The reference server has no authentication.** It is meant to bind to `127.0.0.1`. Exposing it
  on a public interface would give anyone who can reach it read and write access to your notes.
  The provided `ensure-up.sh` binds to loopback for exactly this reason.
- **`create_note` and `update_note` write to disk without a confirmation step.** Version-control
  your vault; that is the intended safety net, and it doubles as a review mechanism for anything
  an agent writes.
- **The server trusts its `VAULT_PATH`.** It refuses paths that escape the vault, but it does not
  sandbox the vault itself.

## Your own setup

Two habits prevent most of the trouble this kind of setup can cause:

- **Never put secrets in a knowledge base.** It is not a password manager, and its whole purpose is
  to surface its contents to an agent.
- **Check before you publish.** Anything derived from a work setup carries host names, user names,
  and internal identifiers in example paths. Grep for them before pushing.
