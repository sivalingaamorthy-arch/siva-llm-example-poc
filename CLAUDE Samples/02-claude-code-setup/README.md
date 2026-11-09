# POC 6: Claude Code project configuration

**Part of [CLAUDE Samples](../README.md) · AI learning journey**
Claude Code configured for a real (small) codebase, with every layer of project configuration in use: **CLAUDE.md, `.claude/rules/`, a skill, a subagent and an MCP server**.

The code is a working FastAPI **health-content API** over the repo's [shared sample data](../../Sample-Data-Health-Content/README.md): it serves the catalog and stores R1/R2/R3 recommendations behind the shared R2 safety rules (8 tests). The app is deliberately ordinary; the `.claude/` folder is the lesson.

> Claude Code reads `CLAUDE.md`, `.claude/` and `.mcp.json` from the directory you launch it in, so **start `claude` from this folder**, not from the repo root.

## Map: which layer does what

```
CLAUDE.md                          always loaded: what the project is, commands, non-negotiables
.claude/rules/api-routes.md        loaded only when routes/** or main.py are touched (paths:)
.claude/rules/tests.md             loaded only when tests/** are touched
.claude/rules/safety-content.md    no paths -> always loaded (R2 safety rule)
.claude/skills/add-endpoint/       /add-endpoint: a repeatable procedure + template.py
.claude/agents/api-reviewer.md     read-only reviewer in its own context window
.claude/settings.json              permissions: allow tests/lint, ask before flag_article, deny .env
.mcp.json                          health-content MCP server (sibling folder ../03-mcp-structured-errors)
```

| Layer | Loaded | Use it for | Don't use it for |
|---|---|---|---|
| `CLAUDE.md` | Every session | Facts every task needs: commands, architecture, hard rules | Long procedures, file-type trivia |
| `rules/` with `paths:` | When matching files are read | Conventions for one part of the tree | Anything that must always apply |
| `rules/` without `paths` | Every session | Cross-cutting policy split out of CLAUDE.md | |
| Skill | Description always; body on demand | Multi-step *how-to* (procedures, templates) | Facts (those go in CLAUDE.md) |
| Subagent | When delegated | Isolated work that would pollute the main context: review, research | Tiny tasks (each spawn starts cold) |
| MCP server | Tools listed at start | Reaching systems outside the repo | Things a CLI already does well |
| `settings.json` | Always | **Enforcement**: permissions | Guidance (that's CLAUDE.md) |

**The principle:** context is a budget. Load each instruction at the narrowest scope where it's still always available when needed. CLAUDE.md is the most expensive real estate you have.

## Try it

```bash
pip install -e ".[dev]" && pytest -q
(cd ../03-mcp-structured-errors && uv sync)   # once, so the MCP server starts fast
claude                                        # from THIS folder
```

1. `/memory`: see CLAUDE.md and the always-on rule loaded, with the path rules absent.
2. "Open `src/health_api/routes/articles.py` and explain it." The `api-routes` rule now appears.
3. `/add-endpoint GET /reports/{report_id}/safe-articles list approved articles that pass the safety rules for a report`: the skill drives the work and calls the reviewer.
4. "Use the api-reviewer agent on my last change": the subagent's verdict comes back in its fixed format.
5. `/mcp`: approve `health-content` (needs `uv`), then "search the catalog for sleep articles".
6. Ask Claude to "let callers pass their own conditions in the request". The always-on safety rule should make it push back.
7. Fix the known gap in CLAUDE.md (422s not in problem+json) and watch the rules steer the change.

Scopes, for the exam: user `~/.claude/` (you, all projects) → project `.claude/` + `CLAUDE.md` + `.mcp.json` (team, committed) → local `CLAUDE.local.md` + `.claude/settings.local.json` (you, this repo, gitignored).

## MY EXPERIENCE
_Notes: which instructions Claude ignored until moved from CLAUDE.md to a hook or permission; how this maps to onboarding docs vs. CI gates in an enterprise team._
