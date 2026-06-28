# JJE knowledge vault

An [Obsidian](https://obsidian.md) vault over the JJE harness's knowledge graph —
the 38 jurors, the research behind them, the three eval passes, and the core
concepts. Open the `vault/` folder as an Obsidian vault to get backlinks + the
graph view.

> **This vault is JJE's own project memory** — the working notes from building and
> dogfooding the harness — and doubles as a worked example of the Hot Cache pattern.
> You do **not** inherit it: the canonical `cp -r .claude .jje` install does not copy
> `vault/`, and your **first `/jje` run auto-seeds a fresh `vault/`** with empty
> skeleton files (`hot.md`/`log.md`/`MOC.md`) in your own repo (skill §10; skipped
> under `interactivity.level: minimal`). Browse this one to see the shape; yours
> starts from those skeletons.

It follows the **Hot Cache** pattern from
[claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian):

- **[hot.md](hot.md)** — the Hot Cache. ~500 words, *overwritten each session*,
  answering "where did we leave off?". **Read this first** (a fresh session or
  agent gets full context without crawling the vault). It is a cache, not a journal.
- **[MOC.md](MOC.md)** — the Map of Content: the master catalog of every note.
- **[log.md](log.md)** — append-only operation log (what was built, when).

## Layout

```
vault/
  hot.md            # Hot Cache — read first
  MOC.md            # master catalog / hub
  log.md            # append-only operation log
  jurors/           # one note per juror (frontmatter: lane, model, tool_backed, eval scores)
  lanes/            # one MOC per lane
  presets/          # one note per preset
  research/         # why the lanes exist (links out to the private lakehouse, never copies it)
  eval/             # the 3 passes + the combined scorecard
  concepts/         # jje-loop, tool-backing, safety-model, interactivity, conventions-overlay
```

## Conventions
- YAML frontmatter (`type`, `tags`, ...), `[[wikilinks]]` between notes,
  `[!callout]` blocks for takeaways/contradictions.
- Notes **link to** the implementation (`.claude/...`, `docs/...`) rather than
  duplicating it — single source of truth.
- The private team lakehouse notes are **linked, never copied** (see
  [research/lakehouse.md](research/lakehouse.md)).

## Keeping the Hot Cache fresh
JJE's own close-out (skill §10) does this automatically after each run — it
overwrites `hot.md` with the new "where did we leave off?" and appends a line to
`log.md`. You can also edit them by hand between runs. That is the whole
maintenance loop.
