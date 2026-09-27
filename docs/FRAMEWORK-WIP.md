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
- **The user's installation is only a user of the framework**: its configuration lives in a separate
  repository next to this one (`../lcars-site`, private). Nothing in this repository names aquariums,
  waste bins, Spotify accounts or other installation details, except as clearly marked examples.
- **Views are composed from components**, declared in **YAML** (for now; Python plugins as escape hatch).
- **Documentation** (installation, dependencies, configuration, components) and **every code comment**
  are reviewed for installation-specific wording.

## Design

See `docs/ARCHITECTURE.md` (written alongside the code). In short:

- Python package `lcars/`: `engine/` (fluid sizes, screen tiers, palette, codes, primitive cards),
  `frame.py` (header, nav, sidebar, mid bar, foot, alert), `components/` (layout and data components,
  registry), `config.py` (YAML loader: `${...}` interpolation, `repeat`, build-time data), `build.py`,
  `setup/` (HACS, config entries, helpers, resources, theme, dashboard; `doctor` checks the same steps),
  `cli.py` (`lcars init|doctor|setup|build|deploy|restore|files`).
- The custom cards and the view theme move into the package (`lcars/www/`, `lcars/themes/`) and are
  deployed by `lcars setup` / `lcars files`.
- Responsive engine: a component renders for a screen *tier* (0 = phone, 1..4 = the display priorities)
  and `phone`; components whose own layout changes with the tier wrap themselves (`responsive()`: renders
  per tier, keeps the distinct variants as `tiered()` / `by_screen()`).

## Plan and status

1. [ ] Package skeleton, engine and frame ported from `generator/build_dashboard.py`
2. [ ] Components and YAML loader; the user's views as YAML in `../lcars-site`
3. [ ] Compare with the old generator's output (normalised JSON diff: codes, blink rates and view order
       ignored), then screenshots old vs new at 1280×720, 1280×800, 1920×1080, 734×337
4. [ ] Generic cards (history instead of power, schedule instead of phases, neutral player texts, tank
       units), theme renamed, comments reviewed
5. [ ] `lcars setup` / `lcars doctor`
6. [ ] Docs: README, INSTALL, CONFIGURATION, COMPONENTS, CARDS, EXTENDING, DESIGN (framework rules only)
7. [ ] Demo configuration (examples/), old generator and tools removed
8. [ ] Deploy to `lcars-dev`, user check; live `lcars-bridge` only after the user's go
