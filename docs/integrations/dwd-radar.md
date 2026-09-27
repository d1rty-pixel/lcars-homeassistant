# DWD precipitation radar

Used by the `radar` component (`custom:lcars-radar`). This is not an HA integration: the card loads
images straight from the Deutscher Wetterdienst's public GeoServer. No account or API key is needed.
**It covers Germany** (and a margin around it).

## How it works

- **Frames**: WMS `https://maps.dwd.de/geoserver/dwd/wms`, layer `dwd:Radar_wn-product_1x1km_ger`
  (composite plus nowcast, 1 km). The card requests one image per 10-minute step for its own
  bounding box: 60 min back to 90 min ahead, relative to the latest analysis (which lags about
  10 min). It loops them and holds briefly on "now" and at the end.
- **Borders**: the WMS forbids custom styles, so the framework fetches the district
  (`dwd:Warngebiete_Kreise`) and state (`dwd:Laender`) outlines from the WFS
  (`https://maps.dwd.de/geoserver/dwd/ows`) **at build time**. It clips them to the map area,
  rounds them to about 100 m and embeds them in the card config as SVG paths.
- **Controls**: the buttons are Play/Pause, Back, Next and Now: in the map's own pillar
  (`controls: pillar`), or in the mid bar (`buttons: {type: radar, controls: row}` in a bar piece,
  linked to a map with `controls: none` on the same view). With the per-device motion switch off
  (`?lcars_motion=off`), it doesn't autoplay, but the buttons still work.

## Configuration

In `lcars.yaml`:

```yaml
radar:
  home: [50.00, 8.00]     # home marker (lat, lon); the map is centred on it
  width_km: 170           # map width
  # center: [50.10, 7.90] # optional: another map centre (lat, lon)
```

Frame timing, colours and the layer are set in the `radar` component (`lcars/components/data.py`).
Rebuild after changing the location, since the borders are fetched for the map area.

## Notes

- **Coverage is Germany** (plus a margin). Outside it the map stays empty (`lcars init` adds a radar
  only where HA's location is in Germany). For other countries, embed another radar card with the
  `card` component; a provider option for the radar card would be welcome.
- **Attribution**: the data is DWD open data. Credit the source ("Deutscher Wetterdienst") when you
  publish screenshots, and check DWD's terms of use.
- The build needs internet access to `maps.dwd.de` for the borders. The browser needs it for the
  frames.
