// Workaround for a load-order race between LCARdS and HA's frontend.
//
// HA's app.js installs @webcomponents/scoped-custom-element-registry, which
// replaces window.customElements. LCARdS is loaded via extra_module_url and
// can finish initialising (and call customElements.define) *before* app.js
// has installed the polyfill. Those elements then exist in the native
// registry only; the polyfill's get()/whenDefined() never see them, so HA
// renders "Custom element doesn't exist" error cards (or a blank view for
// custom:lcards-layout-view).
//
// The polyfill's define() skips the native define when the tag is already
// natively defined, so re-registering the native class is safe. This file is
// a Lovelace resource, which HA loads after app.js.
//
// TAGS is every name lcards.js 2026.09.0 passes to customElements.define;
// regenerate it after an LCARdS update if new elements appear.
const CORE = ["lcards-button", "lcards-elbow", "lcards-chart", "lcards-slider", "lcards-data-grid", "lcards-msd-card", "lcards-alert-overlay", "lcards-select-menu", "lcards-layout-card", "lcards-layout-view"];
const TAGS = ["alert-mode-color-wheel", "hex-alpha-color-picker", "hex-input", "lcards-about-tab", "lcards-alert-overlay", "lcards-alert-overlay-editor", "lcards-animation-editor", "lcards-background-animation-editor", "lcards-border-editor", "lcards-button", "lcards-button-editor", "lcards-card-datasources-list", "lcards-card-picker-wrapper", "lcards-card-sound-tab", "lcards-chart", "lcards-chart-editor", "lcards-chart-series-list-editor", "lcards-chart-studio-dialog", "lcards-collapsible-section", "lcards-color-list", "lcards-color-picker", "lcards-color-section", "lcards-color-section-v2", "lcards-condition-group-editor", "lcards-config-panel", "lcards-connectivity-tab", "lcards-data-grid", "lcards-data-grid-editor", "lcards-data-grid-studio-dialog-v4", "lcards-datasource-browser", "lcards-datasource-editor-tab", "lcards-datasource-studio-dialog", "lcards-dialog", "lcards-elbow", "lcards-elbow-editor", "lcards-filter-editor", "lcards-font-selector", "lcards-form-section", "lcards-global-datasources-panel", "lcards-grid-edit-overlay", "lcards-grid-layout", "lcards-icon-area-picker", "lcards-icon-editor", "lcards-icon-section", "lcards-layout-card", "lcards-layout-card-editor", "lcards-layout-studio-dialog", "lcards-layout-view", "lcards-layouts-tab", "lcards-message", "lcards-msd-card", "lcards-msd-editor", "lcards-msd-live-preview", "lcards-msd-studio-dialog", "lcards-multi-action-editor", "lcards-multi-text-editor-v2", "lcards-object-editor", "lcards-pack-explorer-dialog", "lcards-pack-explorer-tab", "lcards-padding-editor", "lcards-position-picker", "lcards-preview-chip", "lcards-processor-editor", "lcards-processor-tree-editor", "lcards-provenance-tab", "lcards-rule-apply-editor", "lcards-rule-editor-dialog", "lcards-rules-dashboard", "lcards-scope-selector", "lcards-select-menu", "lcards-select-menu-editor", "lcards-shape-texture-editor", "lcards-shell-strategy-editor", "lcards-shield-bubble-diagram", "lcards-slider", "lcards-slider-editor", "lcards-slider-range-visualizer", "lcards-sound-config-tab", "lcards-sound-source-selector", "lcards-storage-explorer-tab", "lcards-style-hierarchy-diagram", "lcards-template-evaluation-tab", "lcards-template-sandbox", "lcards-theme-generator-view", "lcards-theme-token-browser-tab", "lcards-unified-segment-editor", "lcards-users-devices-tab", "lcards-yaml-editor", "lcards-zone-list-editor", "ll-strategy-dashboard-lcars-shell"];

function adopt(tag) {
  if (customElements.get(tag)) return true;
  const ctor = document.createElement(tag).constructor;
  if (ctor === HTMLElement || ctor === HTMLUnknownElement) return false; // not defined by LCARdS yet
  try {
    customElements.define(tag, ctor);
    return true;
  } catch (e) {
    console.warn(`[lcards-registry-fix] could not re-register ${tag}:`, e);
    return true;
  }
}

// LCARdS may still be initialising when this runs; retry for up to ~30 s
// until all core elements are visible to the scoped registry.
let tries = 0;
(function loop() {
  TAGS.forEach(adopt);
  const missing = CORE.filter((t) => !customElements.get(t));
  if (missing.length && ++tries < 60) setTimeout(loop, 500);
  else if (tries) console.info(`[lcards-registry-fix] done after ${tries} retries, missing: ${missing.join(", ") || "none"}`);
})();
