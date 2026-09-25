# Power metering

Used by **Laundry** (washing machine), **Aquarium → Osmosis** (RO unit) and **Aquarium → Power**.

## Setup

Any smart plug that reports power (W) and energy (kWh), e.g. Shelly Plug S Gen3 through the built-in
Shelly integration. The views expect:

| Entity | Needed for |
|--------|------------|
| `switch.<plug>` | the Supply / unit row (tap or hold to switch) |
| `sensor.<plug>_power` with `state_class: measurement` | the value, the level bar, and the power trace |
| `sensor.<plug>_energy` | the Energy row |

Set them in `WASH` and `OSMO` (and `POWER_GRID` for the aquarium's Power page) in the generator.

## Power trace (`custom:lcars-power`)

- The data comes from HA's **long-term statistics** (`recorder/statistics_during_period`, the maximum
  per period): 5-minute periods for 24 h, hourly for 7 d and 28 d. The sensor must have
  `state_class: measurement`, or there are no statistics.
- Log scale with lines at 1, 10, 100 and 1000 W. Range buttons 24H / 7D / 28D in the pillar; the
  choice is stored per browser.
- "Running" on the Laundry page means above 3 W (`WASH_RUNNING`). The level bar goes up to 2000 W
  (`WASH_MAX`).
