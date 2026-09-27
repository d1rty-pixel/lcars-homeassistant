"""`lcars diag`: add a diagnostic view "diag" to the dashboard: what a device's browser reports about its
viewport (window and visual viewport, 100vh/dvh/svh/lvh, safe-area insets as the browser and as HA see them,
the phone media query, user agent). Open <dashboard>/diag on the device to read them. Run it again after
every deploy (deploy replaces the whole configuration); best on a test copy: lcars --dashboard <copy> diag.
"""
PROBE = ("const probe = (css) => { const d = document.createElement('div'); d.style.cssText = "
         "'position:fixed;left:0;top:0;visibility:hidden;' + css; document.body.appendChild(d); "
         "const r = d.getBoundingClientRect(); const c = getComputedStyle(d); "
         "const cs = {paddingTop: c.paddingTop, paddingRight: c.paddingRight, paddingBottom: c.paddingBottom, "
         "paddingLeft: c.paddingLeft}; d.remove(); return [r, cs]; }; ")
lines = [
    "'window ' + innerWidth + ' × ' + innerHeight + ' · visual viewport ' + Math.round(visualViewport.width) + ' × ' + Math.round(visualViewport.height) + ' · DPR ' + devicePixelRatio",
    "['vh','dvh','svh','lvh'].map(u => '100' + u + ' = ' + Math.round(probe('height:100' + u)[0].height)).join(' · ')",
    "(() => { const cs = probe('padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)')[1]; return 'safe area t/r/b/l ' + [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft].join(' '); })()",
    "(() => { const cs = probe('padding:var(--safe-area-inset-top,0px) var(--safe-area-inset-right,0px) var(--safe-area-inset-bottom,0px) var(--safe-area-inset-left,0px)')[1]; return 'HA safe area t/r/b/l ' + [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft].join(' '); })()",
    "'phone query (max-height: 520px): ' + matchMedia('(max-height: 520px)').matches + ' · screen ' + screen.width + ' × ' + screen.height",
    "navigator.userAgent.slice(0, 90)",
]


def add_view(site):
    """Add (or replace) the "diag" view of the site's dashboard."""
    cards = []
    for i, js in enumerate(lines):
        cards.append({"type": "custom:lcards-button", "entity": "sensor.time", "preset": "text-only",
                      "show_icon": False, "min_height": 0, "view_layout": {"grid-area": f"l{i}"},
                      "text": {"t": {"content": "[[[ " + PROBE + "return " + js + "; ]]]", "position": "center-left",
                                     "font_size": 14, "color": "#FFCC99"}}})
    view = {"title": "diag", "path": "diag", "type": "custom:lcards-layout-view", "theme": site.theme,
            "layout": {"grid-template-columns": "1fr", "grid-template-rows": " ".join(["36px"] * len(lines)),
                       "grid-template-areas": " ".join(f'"l{i}"' for i in range(len(lines))), "grid-gap": "4px",
                       "padding": "8px"}, "cards": cards}
    ha = site.ha()
    cfg = ha.result({"type": "lovelace/config", "url_path": site.url_path})
    cfg["views"] = [v for v in cfg["views"] if v.get("path") != "diag"] + [view]
    ha.result({"type": "lovelace/config/save", "url_path": site.url_path, "config": cfg})
    print(f"added /{site.url_path}/diag")
