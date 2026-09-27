# Work in progress: the framework (branch `framework`)

Status notes for turning the generator into a framework. Read this first when continuing; delete it (and
its pointer in `AGENTS.md`) before merging to `main`. Branched from `responsive-small-screens` after its
scrolling round was committed (`docs/RESPONSIVE-WIP.md` still applies to the responsive work).

## Goal and user decisions (2026-09-27)

- **A framework, not one installation's dashboard.** A responsive LCARS UI system on top of LCARdS: layout
  engine, component library, page frame, navigation. It also **sets Home Assistant up itself** (LCARdS and
  the other dependencies, theme, resources, helpers, dashboard) as far as HA's APIs allow ("falls möglich
  soll das ding alles selbst tun").
- **Other people must be able to use it out of the box**: install, `lcars init`, `lcars setup`, build their
  own views from the same components.
- **The user's installation is only a user of the framework**: its configuration lives in a separate,
  private repository next to this one (`../lcars-site`). Nothing in this repository names aquariums,
  waste bins, Spotify accounts or other installation details, except as clearly marked examples.
- **Views are composed from components**, declared in **YAML** (for now; Python plugins as escape hatch).
- **Documentation** (installation, dependencies, configuration, components) and **every code comment**
  reviewed for installation-specific wording.
- Names chosen without asking (easy to change): package `lcars` / distribution `lcars-homeassistant`,
  command `lcars`, view theme **"LCARS Bridge"** (was "LCARS Aquarium"), cards under `/config/www/lcars/`.

## Status (2026-09-27)

Done and committed on `framework`:

1. Package `lcars/` (engine, frame, components, config loader, build, CLI), pip-installable.
2. The user's 11 views as YAML in `../lcars-site/lcars.yaml` (its own git repo). Checked: normalised JSON
   diff against the old generator's output, then screenshots of the old build vs the new at 1280×720,
   1280×800, 1920×1080, 734×337: layout identical on every page (remaining pixel differences: LCARS
   numbers from new keys, the number columns' sensor pick, clock, camera, chart data).
3. Cards generic: `lcars-history` (was `lcars-power`), `lcars-schedule` (was `lcars-phases`) with the old
   names as aliases; tank with units and a container query; player/library status texts by `name`;
   sliders for number, input_number and lights; every comment reviewed.
4. `lcars setup` / `doctor` / `init` / `files` / `diag`. Run against the user's HA: setup copied the
   cards to `/config/www/lcars/`, created their resources, **removed the old `/local/lcars-*.js`
   resources** (the files are still in `/config/www/`, unused), installed the theme "LCARS Bridge" (the
   old "LCARS Aquarium" file is still there; the live dashboard uses it until its next deploy). The live
   `lcars-bridge` dashboard (still the old main-branch build) was checked by screenshots before and
   after: unchanged. A second run changes nothing.
5. Docs rewritten: README, INSTALL, CONFIGURATION, COMPONENTS, CARDS, EXTENDING, DESIGN (framework rules
   only), OPERATIONS, NOTES, integrations/. The installation's page descriptions moved to
   `../lcars-site/PAGES.md`, its aquarium notes to `../lcars-site/AQUARIUM.md`.
6. Examples (`examples/minimal.yaml`, `examples/home.yaml`, `examples/plugins/note.py`) build and
   validate; `home.yaml`'s new combinations were checked on `lcars-dev` (with made-up entities).
7. The old generator, `tools/deploy.py`, `deploy_ha_files.sh`, `diag_view.py`, `gen_registry_fix.py`,
   `bump_resources.py` and `site.example.yaml` are gone.

`lcars-dev` holds the user's configuration built by the framework. **Live since 2026-09-27** (user's go):
`lcars-bridge` is deployed from `../lcars-site`; the old theme file, the old `/config/www/lcars-*.js`
files and the hidden old dashboard `aquarium-lcars` are deleted (its config is backed up in
`../lcars-site/build/backups/`).

## Open

- Not tested on a fresh HA: HACS downloads and config flows (`lcars setup` on an HA without LCARdS /
  kiosk-mode / Time & Date / the dashboard), the `configuration.yaml` themes include, the restart path.
  Every one of these steps found its state already right on the user's HA. A throwaway HA (container or
  VM) would test them.
- The radar is DWD only (Germany); a provider for other countries would be a new radar card option.
- The responsive branch's open issues (`docs/RESPONSIVE-WIP.md`) are unchanged.
- Candidates: bundle the Antonio font (offline kiosks), HACS installability of the cards themselves.
