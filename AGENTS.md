# Agent entry point

1. **Read `docs/agent_execution_guide.md` first.** It is the single source of what is approved, in what order, and how each item is validated. Do not start work that is not in its queue.
2. Design contracts live in `docs/design_*.md`. The guide points at them; read the sections an item names before writing code.
3. Findings, open decisions and deferred features live in `docs/ongoing_general_errors.md`. **Never fill in a `Your selection: _____` line.** It belongs to the user.
4. Commits follow `.agents/skills/commit_message_guidelines/SKILL.md`: one item, one Conventional Commit, the WHY in the body. Issues follow `.agents/skills/bug_documentation_guidelines/SKILL.md`.
5. Read exit codes bare, falsify every gate, open every artefact you produce, and never loosen a bar to pass it.
