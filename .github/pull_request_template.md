## What changes

<!-- one or two lines: what the user notices -->

## Changelog

[...autoGenerate]

## Checklist

- [ ] `VERSION` bumped (merging into `main` creates the tag `vX.Y.Z` and the release)
- [ ] `./run-tests.sh` ends with `ALL GREEN` (`RUN_E2E=1` when the page changed)
- [ ] New page text is English (`t("…")` or `data-i18n`) with its line in `PT_BR` in `web/i18n.js`
- [ ] New tray or notification text is English inside `tr()` with its line in `PT_BR` in `server/i18n.py`
- [ ] Changed the WebSocket protocol? Updated `_dispatch` (web.py), `input_device.py`, `app.js` and the table in `CLAUDE.md`
- [ ] Changed `pyproject.toml`? Ran `uv lock` and exported both `requirements*.txt`
- [ ] Tested with a real phone on the LAN when the page, the server or the install changed
