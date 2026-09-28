# Installation

The short way:

```bash
python3 -m venv ~/.venvs/lcars && ~/.venvs/lcars/bin/pip install git+https://github.com/d1rty-pixel/lcars-homeassistant
export PATH=~/.venvs/lcars/bin:$PATH                     # or: pipx install git+https://...
mkdir -p ~/.config/homeassistant && echo "<long-lived token>" > ~/.config/homeassistant/token
mkdir my-lcars && cd my-lcars
lcars init --url http://homeassistant.local:8123         # writes lcars.yaml from what HA has
                                                         # (or: copy examples/lcars.example.yaml)
lcars setup                                              # installs and sets up what the dashboard needs
lcars deploy                                             # builds the dashboard and saves it to HA
```

Then open `http://homeassistant.local:8123/lcars-bridge/` (reload once). The rest of this page explains
what these steps need and do, and how to do each by hand.

## What you need

**Home Assistant** with its dashboards in the default storage mode (tested with HA 2026.9):

- **HACS**, installed and linked to GitHub once ([hacs.xyz](https://hacs.xyz/docs/use/)). `lcars setup`
  installs LCARdS and kiosk-mode through it. Without HACS, install those two by hand (below).
- **An admin user's long-lived access token** (your profile → Security → Long-lived access tokens), in
  `~/.config/homeassistant/token` (mode 600) or in `HA_TOKEN`.
- **File access to HA's `/config`** for the cards and the view theme, which HA's APIs can't write (see
  [File access](#file-access)). Without it, copy two things by hand.

**Your computer** (or the HA host itself): Python 3.10 or newer (tested with 3.12), and `ssh` for the
`ssh` file access. The package needs PyYAML and jsonschema; pip installs them.

## What `lcars setup` does

Every step checks first and changes only what isn't right, so it's safe to run again (after an update
of this package, or of LCARdS). `lcars doctor` runs the same checks without changing anything, and
checks the configuration and its entities too.

| Step | Checks | Does |
|------|--------|------|
| connection | HA reachable, the token accepted | |
| hacs | HACS installed | (install it by hand) |
| lcards | [LCARdS](https://github.com/snootched/lcards) downloaded and set up | downloads it through HACS; after the restart, creates its config entry |
| kiosk-mode | [kiosk-mode](https://github.com/NemesisRE/kiosk-mode) downloaded | downloads it through HACS (HACS adds its resource) |
| card-mod | card-mod isn't a resource while UIX is installed | warns (UIX refuses to set up otherwise) |
| files | the cards (`/config/www/lcars/*.js`) and the view theme (`/config/themes/lcars_bridge.yaml`) up to date | copies what differs; writes the LCARdS registry workaround for the installed LCARdS version |
| themes | the view theme loaded | reloads themes; if `configuration.yaml` doesn't include the themes directory, adds `frontend: themes: !include_dir_merge_named themes` (backup: `configuration.yaml.lcars-backup`) |
| resources | a Lovelace resource per card (`/local/lcars/<card>.js?v=<content hash>`) and the Antonio font | creates or updates them; removes resources of an install from before the framework (`/local/lcars-*.js`) |
| time | `sensor.time` | sets up the Time & Date integration with the Time sensor (it re-renders the clock every minute) |
| helpers | `input_boolean.lcars_bars`, `input_text.lcars_alert_ack` | creates them: the global switch for the segment bars (on, `?lcars_bars=off`), the acknowledged alerts |
| dashboard | the dashboard `dashboard.url_path` | creates it (storage mode) |

When an integration was downloaded or `configuration.yaml` changed, HA needs a restart: `lcars setup`
asks (`--yes`: restarts without asking), waits for HA and runs the steps again. `lcars files` runs only
files, themes and resources.

Not installed, because the dashboard doesn't need them:

- [HA-LCARS](https://github.com/th3jesta/ha-lcars): the view theme stands alone (it doesn't extend
  HA-LCARS, whose card styles would paint embedded standard cards lavender). Install it if you want
  LCARS themes for HA's other pages; the dashboard is unaffected.
- [UIX](https://github.com/Lint-Free-Technology/uix): only for embedded standard cards (`card`
  components): with UIX they get a black, borderless style. The theme's card variables do most of it
  without UIX.
- LCARdS' sound helpers: sounds are off until you create them in LCARdS' config panel (Helpers tab)
  and switch them on ([LCARdS: sounds](https://lcards.unimatrix01.ca/configuration/sounds)).

## File access

`homeassistant.files` in `lcars.yaml` says how `lcars setup` reaches `/config`:

| Method | When | Configuration |
|--------|------|---------------|
| `ssh` | from your computer, through an SSH add-on | `{method: ssh, login: user@host, options: [...], sudo: true}` (`config_dir` if HA's configuration isn't at `/config` there) |
| `local` | `lcars` runs on the HA host itself (e.g. in the Terminal add-on) | `{method: local}` (`config_dir` if not `/config`) |
| `none` | no file access | copy by hand (below); `lcars setup` says what |

For `ssh`, the [Advanced SSH & Web Terminal](https://github.com/hassio-addons/addon-ssh) add-on works:
set a username and your public key in its configuration (`/config` is HA's configuration there, `sudo`
is available). The host needs no `scp`/`sftp`: files go through `cat` and `tee`. Load your key into the
agent (`ssh-add`) if it has a passphrase; `lcars` uses `BatchMode` and won't ask. With a login that is
root already, set `sudo: false`. `lcars doctor` shows whether the access works (step files).

## Doing it by hand

Where `lcars setup` can't (no HACS, no file access), these are the equivalents:

1. **LCARdS**: download `lcards.zip` from its [latest release](https://github.com/snootched/lcards/releases),
   extract it to `/config/custom_components/lcards/`, restart HA, then Settings → Devices & services →
   Add integration → LCARdS.
2. **kiosk-mode**: download `kiosk-mode.js` from its
   [latest release](https://github.com/NemesisRE/kiosk-mode/releases) to `/config/www/community/kiosk-mode/`
   and add `/local/community/kiosk-mode/kiosk-mode.js` as a JavaScript module resource (Settings →
   Dashboards → ⋮ → Resources).
3. **Files**: copy the package's `lcars/www/*.js` to `/config/www/lcars/` and `lcars/themes/lcars_bridge.yaml`
   to `/config/themes/` (`pip show -f lcars-homeassistant` shows where the package is). Make sure
   `configuration.yaml` has
   ```yaml
   frontend:
     themes: !include_dir_merge_named themes
   ```
   and restart HA (after that, Developer tools → YAML → Reload themes is enough).
4. **Resources**: add every `/local/lcars/<file>.js` as a JavaScript module, and
   `https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&display=swap` as a stylesheet. After
   updating the files, change the `?v=` of their URLs, so browsers load the new ones.
5. **Time & Date**: Settings → Devices & services → Add integration → Time & Date → Time.
6. **Helper**: Settings → Devices & services → Helpers → Create → Toggle, named `LCARS bars`, on.
7. **Dashboard**: Settings → Dashboards → Add dashboard → New dashboard from scratch, URL `lcars-bridge`.

Then run `lcars doctor` to see whether anything is missing, and `lcars deploy`.

## Deploying

`lcars deploy` builds the dashboard, checks every LCARdS card against LCARdS' JSON schema (and refuses
to save a dashboard that fails), saves the live configuration to `build/backups/` and saves the new one.
`lcars restore build/backups/<file>.json` puts a backup back. `--dashboard <path>` works on another
dashboard, e.g. a hidden, admin-only test copy you try changes on first.

Rebuild after changing `lcars.yaml`, and after changes to what is read at build time: `data` sources,
the radar's location, entity patterns such as `media_player.spotify_*`, and the sensors of the header's
number columns.

## Kiosk tablets

- Use a non-admin HA user for wall screens and set the kiosk browser's start URL (Fully Kiosk: Settings
  → Web Content Settings → Start URL), e.g. `https://<your-ha>/lcars-bridge/<view>?lcars_motion=off`.
- `?lcars_motion=off` turns the animations off for that browser (stored in it; the sidebar's "Motion"
  block toggles it). Older tablets' renderers crash with all of LCARdS' animations running.
- Don't give the user an LCARS *profile* theme if they also use other dashboards: every view here
  carries its own theme.
- Sounds play only after the first touch; allow media playback in the kiosk browser's settings.
- `?disable_km` shows HA's header and sidebar again (kiosk-mode), e.g. to edit.

## Updating

```bash
pip install -U git+https://github.com/d1rty-pixel/lcars-homeassistant
lcars setup      # copies the changed cards, updates their resources (and the registry workaround)
lcars deploy
```

After an **LCARdS update** (through HACS), run `lcars files`: the registry workaround needs the new
version's element names. Browsers pick up new cards through the changed `?v=` on reload.

## Uninstalling

Delete the dashboard (Settings → Dashboards), the resources `/local/lcars/*` and the Antonio font,
`/config/www/lcars/`, `/config/themes/lcars_bridge.yaml` and the helpers `input_boolean.lcars_bars` and `input_text.lcars_alert_ack`;
remove LCARdS and kiosk-mode through HACS if nothing else uses them.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| "Custom element doesn't exist" / configuration errors on every card, especially through a reverse proxy | LCARdS sometimes registers its elements before HA's scoped registry polyfill is installed; `lcards-registry-fix.js` re-registers them. Run `lcars files` after every LCARdS update. |
| A value shows as `[[[ return … ]]]` | Its entity doesn't exist (LCARdS evaluates templates only with an entity). `lcars build` and `lcars doctor` list missing entities. |
| Standard cards look lavender | HA-LCARS' card styles leaked in: the view theme must be `LCARS Bridge` (it declares its own UIX theme). |
| Page half-rendered after a deploy | Frontend state: hard-reload (Ctrl+Shift+R). |
| `lcars setup` / `lcars build` fail with "Permission denied (publickey)" | The SSH key for `homeassistant.files` isn't loaded (`ssh-add`). |
| The theme isn't loaded after `lcars setup` | `configuration.yaml` includes themes from elsewhere, or HA wasn't restarted after adding the include. |
| The tablet's renderer crashes | Turn animations off (`?lcars_motion=off`); avoid pages with hundreds of LCARdS buttons (use the light cards). |

More root causes in [NOTES.md](NOTES.md).
