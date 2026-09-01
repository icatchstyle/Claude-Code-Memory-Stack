# 3 — Writing a `CLAUDE.md` that survives contact with reality

`CLAUDE.md` is loaded in full, on every prompt, in every session. That makes it the most
expensive text you will ever write and the most powerful. Both facts point the same way: **make
it short, make it normative, make it maintain itself**.

The annotated starting point is [`setup/CLAUDE.md.template`](../setup/CLAUDE.md.template).

**In this chapter:** [Scope levels](#scope-levels) · [What belongs in it](#what-belongs-in-it) · [What must not be in it](#what-must-not-be-in-it) · [The recall rule, written correctly](#the-recall-rule-written-correctly) · [Make the file maintain itself](#make-the-file-maintain-itself) · [Maintaining this file](#maintaining-this-file) · [Length](#length)

## Scope levels

| File | Scope | Use for |
|---|---|---|
| `~/.claude/CLAUDE.md` | You, everywhere | Personal working style, autonomy limits, vault access |
| `<repo>/CLAUDE.md` | One project, everyone | Build commands, test commands, project conventions |
| `<repo>/CLAUDE.local.md` | One project, you | Local paths and overrides — gitignore it |

Project files are checked in and read by your colleagues too, so write them for a stranger. Keep
personal preferences out of them.

## What belongs in it

Six categories, in rough order of value:

1. **Autonomy limits.** The most valuable lines in the file. What may the agent do unasked, and
   what needs your word first? Be specific and enumerate: *"Never `commit`, `merge`, `push`,
   `pull`, or open an MR without an explicit request."* A vague "be careful" achieves nothing.
2. **Access rules.** Which tool reaches which resource, and which paths are forbidden. *"The vault
   is reached only through `mcp__vault__*` — never `Read`/`Write`, never a shell fallback."*
   Without this, the agent will happily bypass your MCP server and skip its indexing, validation,
   and write guards.
3. **The recall obligation.** The rule that makes the vault work at all. See below.
4. **Output conventions.** Language of prose vs. language of code comments, comment density, TODO
   format, commit-message style.
5. **Environment facts that are genuinely constant.** The one vault path. The names of MCP servers
   and what each is for. A *pointer* to the DB-profile note — not the list of profiles.
6. **Self-maintenance rules.** What the agent may change in this file without asking.

## What must not be in it

- Lists of hosts, URLs, account IDs, database profiles, service inventories. These change, and
  each one is a permanent tax. Put them in `GLOBAL/config/` and link.
- Architecture descriptions. Vault.
- Step-by-step procedures. Skill.
- Anything you have not verified this month.

**The test:** for each line ask *"does this change what the agent does, in most sessions?"* If it
only changes what the agent *knows*, cut it and leave a pointer.

## The recall rule, written correctly

This is the hardest rule to get right, and the one that decides whether your vault is a knowledge
base or a graveyard. Two failure modes:

- *Too soft* — "consult the knowledge base when it seems relevant." The agent will nearly always
  decide it is not relevant, because missing knowledge is invisible. **Nothing gets looked up.**
- *Too hard* — "always search before answering, no exceptions." Now "yes" and "thanks" trigger
  searches. **The user disables the rule within a week.**

The shape that works: **mandatory by default, with a short closed list of exemptions**, plus an
explicit warning against the model's own judgement.

```markdown
### Knowledge recall (binding)

Before every task — without exception — run a gotcha check with the context (project,
technologies, paths) AND a search with one or two precise terms.

Only these three cases are exempt:
- a pure follow-up about the current conversation (the knowledge is already in context),
- a bare confirmation or abort ("yes", "go on", "stop"),
- the same search was already run this session for the same question.

Do not talk yourself out of it as "trivial". Questions that sound like general knowledge often
have a project-specific answer here (profiles, paths, gotchas, workflows). Missing knowledge
leaves no visible gap in the context — so the list above decides, not your intuition.

If the search finds nothing, continue normally. Recall is an accelerator, not a gate.
```

Three details doing real work in that text:

- **The closed exemption list** makes the rule livable, so it does not get switched off.
- **"Do not talk yourself out of it as trivial"** pre-empts the exact rationalisation the model
  otherwise makes.
- **"Recall is an accelerator, not a gate"** stops the agent from stalling when the vault is empty
  — critical in week one, when it is.

Pair it with the `UserPromptSubmit` hook in [`06-hooks.md`](06-hooks.md). The file states the rule
once per session; the hook restates it every turn. Both are needed: instructions decay as context
grows.

## Make the file maintain itself

Give the agent explicit permission to correct this file, with a clear boundary between fixing and
changing:

```markdown
## Maintaining this file

Allowed without asking:
- Correcting facts that are demonstrably stale (paths, ports, server names, versions) —
  verify against the real state first, never from memory.
- Adding new operational knowledge that belongs here: a new MCP server, a changed workflow.
- Tidying: merging duplicates, reducing content to a pointer at its authoritative source,
  removing dead links.

Only with my approval:
- Changing, weakening, or removing a RULE — autonomy limits, language, access rules.
  Shortening is housekeeping; changing meaning is my decision.

Always: this is an instruction file, not a knowledge file. Details go in the vault; only what
steers behaviour stays here. Say at the end of the turn what you changed and why.
```

The fix/change distinction is what makes this safe. Without it you either get a file nobody
updates, or an agent quietly editing its own constraints.

## Length

Aim for **150–300 lines**. Past that, audit: almost everything above 300 lines is a fact that
wants to be in the vault. When you cut a section, replace it with one line naming where it went —
that pointer is often more useful than the section was, because it survives the next change.

Next: [`04-skills.md`](04-skills.md).
