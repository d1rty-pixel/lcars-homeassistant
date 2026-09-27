# Working on this repository

A framework for LCARS dashboards in Home Assistant, on top of LCARdS: a Python package (`lcars/`, the
`lcars` command) that builds a dashboard from a site's YAML configuration, plus light custom cards and a
view theme it installs into HA. There is no dashboard YAML to edit by hand: change the framework or a
site's `lcars.yaml`, build and deploy.

**Branch `framework`: work in progress. Read `docs/FRAMEWORK-WIP.md` first** (and
`docs/RESPONSIVE-WIP.md` for the responsive work it continues). Remove this line and those files before
merging.

## Where things are

- `lcars/`: the framework. `config.py` (the YAML and the model), `build.py`, `frame.py` (the page
  frame), `components/` (the component types), `engine/` (sizes, screen tiers, palette, primitive
  cards), `setup.py` (`setup` / `doctor` / `init`), `www/` (the cards), `themes/` (the view theme).
  [docs/EXTENDING.md](docs/EXTENDING.md) has the module map.
- `docs/DESIGN.md`: **every design rule**. Read it before changing a layout or a component; keep it in
  step with every design change.
- `docs/CONFIGURATION.md`, `docs/COMPONENTS.md`: the reference users work from; keep them in step with
  the code (every field of every component).
- `docs/INSTALL.md`, `docs/OPERATIONS.md` (layout checks, screenshots), `docs/CARDS.md`, `docs/NOTES.md`
  (LCARdS gotchas), `docs/integrations/`.
- `examples/`: configurations that must keep building (`minimal.yaml`, `home.yaml` uses every component).
- A site's configuration lives outside this repository (its own `lcars.yaml`, plugins, `build/`).

## Build and deploy

```bash
pip install -e .                                   # the lcars command (or: PYTHONPATH=<repo> python3 -m lcars)
cd <site> && lcars build                           # build/lcars_dashboard.json, lists missing entities
python3 -m lcars.validate build/lcars_dashboard.json
lcars --dashboard <test-copy> deploy               # try it on a test dashboard first
lcars setup                                        # after changing lcars/www/*.js or the theme (copies, bumps ?v=)
lcars deploy                                       # backs up the live config to build/backups/ first
lcars restore build/backups/<file>.json
```

## Rules that are easy to miss

- **Check layouts at 1280×720, 1280×800, 1920×1080 and a phone (734×337, 20 px bottom inset)** after any
  layout change (screenshots: see `docs/OPERATIONS.md`). No page may scroll (only on phones, below
  `scroll_min_h`, the sidebar and content do); content that doesn't fit is not rendered (display
  priorities), shoulders go first.
- **One layout for all screens**: write sizes as fluid lengths (`fl()`, `font()`, the constants in
  `engine/sizes.py`), not plain px; only placement changes per screen, through tiers.
- Follow the page frame and colour rules in `docs/DESIGN.md` (one label column, titles in bars, one
  colour family per frame, pills via `pill_shape()`, codes via `lcars_code()`, palette names only). All
  UI text is English.
- Card behaviour belongs in `lcars/www/*.js`, sizes and colours come from the component's config. Keep
  the cards' `fluid()` helpers in step with `engine/sizes.py`. Renamed elements stay registered under
  their old names (dashboards built before must keep working).
- Refactoring: build a site before and after and compare the JSON (LCARS numbers and blink rates may
  change with keys; nothing else should).
- `lcars setup` must stay idempotent: check first, change only what isn't right.
- Test interactive changes in a browser without side effects on real devices (e.g. stub the service
  call) when pressing a button would change real state.

## Public repository: no site data

The repository is public. Tracked files stay generic: no hostnames, IPs, names, coordinates, serials or
entity IDs that identify an installation (examples use made-up ones). Site-specific notes belong in the
site's own repository or the git-ignored `CLAUDE.local.md`. Before every push, search the tracked files
for the installation's identifiers (the local notes keep the exact check).
