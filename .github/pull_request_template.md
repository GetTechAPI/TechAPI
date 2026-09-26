<!-- PR title must follow Conventional Commits, e.g. feat(data/cpu): add EPYC Rome SKUs -->

## What & why

<!-- What does this change and why? Link the workstream tracker with "Closes #N": #295 new records, #296 data accuracy, #297 engine/bot/CI, #19 site, #1 releases and dumps. pr-metadata adds it automatically if missing. Auto-close is disabled for tracking issues. -->

## Source

<!-- Cite the upstream source (vendor product page, Wikipedia infobox, datasheet). -->

## Checklist

- [ ] The PR targets `develop` (`main` only moves through release PRs)
- [ ] `python -m app.validate` passes locally
- [ ] Files live at the correct `data/<category>/<...>/<slug>.json` path
- [ ] Slugs are kebab-case and unique within the category
- [ ] `source_urls` cites at least one canonical reference
