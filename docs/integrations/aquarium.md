# Aquarium

The **Aquarium** section is the most installation-specific part of this repo. It shows what the
original installation's aquarium automation exposes. Use it as an example of the reference style, or
map it to your own entities.

## What it expects

| Source | Entities (defaults) | Views |
|--------|---------------------|-------|
| Custom aquarium integrations (manager, pump, CO₂, light schedule, dosing, water change). **Not published here.** | `switch.aquarium_*_mode`, `sensor.aquarium_water_change_status`, `sensor.aquarium_total_power`, `sensor.switch_*_status`, `switch.switch_co2_anlage_automatic_coupling`, `sensor.dose_<channel>_status`, `number.dose_<channel>_fill_level`, `switch.dose_<channel>_schedule`, the light's `*_current_phase` and `*_automatic_schedule` | Status, Light, Dosing |
| [Chihiros LED control](https://github.com/TheMicDiet/chihiros-led-control) (HACS), a Chihiros WRGB II light over BLE | `light.<area>_<light>_rgb`, `number.<light>_rgb_<red/green/blue>_channel`, `sensor.<area>_<light>_last_notification` | Light (transporter sliders, device log) |
| Shelly plugs | pump plug (status, heater flag, power), light plug, CO₂ valve plug, RO unit | Status, Power, Osmosis |
| ESPHome camera | `camera.*` | Visual (through `custom:timed-camera-card`, not in this repo) |

The device-derived parts of these IDs are in `site.yaml` (`devices.pump_plug`, `devices.light`,
`devices.light_area`). The rest are constants at the top of the generator (`PUMP`, `CO2`, `PHASE`,
`CHANNEL`, `DOSE_CHANNELS`, `POWER_GRID`, …).

## Build-time data

The **Light** page draws the day's light phases (`lcars-phases.js`). No entity exposes the schedule,
so the generator reads `/config/aquarium_light_control.yaml` from the HA host over SSH at build time
(`light_phases()`). Each phase has `name`, `start`, `end`, `ramp_up_minutes`, `ramp_down_minutes` and
`levels` (a percentage per channel). Rebuild after changing the schedule. Without such a file, drop
the phases card or feed `light_phases()` from elsewhere.

## Pump alert

On **every page**, the title turns into a blinking red alert when the circulation pump's status
sensor (`PUMP`) reports `Critical`, and a yellow warning on `Warning` / `Off`. It reads the
`critical_minutes` and `minutes_left` attributes. Point `PUMP` at your own status sensor, or remove
the override in `frame()`.
