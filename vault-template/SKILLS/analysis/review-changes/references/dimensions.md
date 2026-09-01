# Review dimensions

One checklist per dimension. Read only the dimension you are working on — that is the whole
reason this file is separate from `SKILL.md`.

## Correctness

- Off-by-one, boundary conditions, empty collections, `null`/`None` paths
- Error handling: swallowed exceptions, errors logged and then ignored
- Concurrency: shared mutable state, check-then-act races, missing locks
- Resource lifetime: files, connections, handles not closed on the error path
- Type/unit confusion: seconds vs. milliseconds, cents vs. euros, 0- vs. 1-based

## Security

- Injection: SQL, shell, template, path traversal
- Authentication and authorisation: is every new endpoint actually covered?
- **Comparisons that must agree but do not** — e.g. case-sensitive in SQL, case-insensitive in
  the application. This class of bug is quiet and expensive.
- Secrets in code, in logs, or in error messages returned to a caller
- Deserialisation of untrusted input

## Performance

- Queries inside loops (the N+1 shape)
- Unbounded result sets — no limit, no pagination
- Repeated work that could be hoisted or cached
- Synchronous I/O on a hot path

## Tests

- Does the change alter behaviour that no test covers?
- Do the new tests assert on the behaviour, or only on the implementation?
- Is there a test for the failure path, not only the happy one?

## Reporting bar

Report a finding only when you can name **concrete inputs or state that produce a wrong output
or a crash**. Everything else is a preference, and preferences dilute the findings that matter.
