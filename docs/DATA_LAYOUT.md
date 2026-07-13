# Data layout

Versioned records stay in `data/`; the directory name is the record family and
the JSON file is the individual record.  Do not group records by a transient
import run or by a scraper name.

## Games

Game records use a deterministic shard:

```
data/game/<slug first two characters>/<slug>.json
```

For example, `hades` belongs at `data/game/ha/hades.json`.  This keeps a
large import stable and prevents one directory from becoming a bottleneck.

## Local checkout policy

The default checkout deliberately excludes `data/` and generated `site/`
content.  They remain tracked and are still present on the remote; omitting
them only prevents routine Git polling from scanning millions of files.

For a focused data import, temporarily add only the family you need:

```
git sparse-checkout add data/cpu
```

For a full game import, add `data/game` for the duration of the import, then
return to the small default checkout:

```
git sparse-checkout add data/game
git sparse-checkout set --cone .github app docs TechEngine
```

Never use `assume-unchanged` or `skip-worktree` as an import workflow.  Run
`python -m app.validate` only while the needed data family is checked out.
For the million-record game import, use the streaming validator:

```
python -m app.validate --category game
```
