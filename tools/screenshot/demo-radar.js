// Made-up radar frames for shot.js with DEMO=...: answers the radar card's DWD WMS requests (GetMap for a
// bounding box and a time) with an SVG of a rain front crossing the map from the south-west, so the
// README's radar shows weather whatever the sky over the example's location does.
const CELLS = (() => {
  // cells along a band through the map's centre, in km from it; deterministic
  let seed = 42;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const cells = [];
  for (let i = 0; i < 90; i++) {
    const along = -170 + 340 * rnd(), across = (rnd() - 0.5) * (rnd() < 0.8 ? 30 : 90);
    // the band runs SW-NE: rotate by 35°
    const a = 35 * Math.PI / 180;
    cells.push({x: along * Math.cos(a) - across * Math.sin(a) - 40, y: along * Math.sin(a) + across * Math.cos(a) - 25,
                r: 2.5 + 9 * rnd() ** 2, level: rnd() ** 1.4});
  }
  return cells;
})();
const COLOURS = ["#9fe3f5", "#50b4ff", "#1e78ff", "#1ec83c", "#f0e61e", "#ff961e", "#ff3c1e"];

module.exports = function radarSvg(url) {
  const q = new URL(url).searchParams;
  const W = +q.get("width") || 600, H = +q.get("height") || 400;
  const [s, w, n, e] = (q.get("bbox") || "0,0,1,1").split(",").map(Number);
  const lat = (s + n) / 2;
  const kmW = (e - w) * 111.32 * Math.cos(lat * Math.PI / 180), kmH = (n - s) * 111.32;
  const t = Date.parse(q.get("time") || new Date().toISOString());
  const min = (t - Date.now()) / 60e3;                 // minutes from now: the front moves 0.7 km/min ENE
  const dx = 0.62 * min, dy = 0.3 * min;
  const px = (x) => W / 2 + (x + dx) * W / kmW, py = (y) => H / 2 - (y + dy) * H / kmH;
  const k = W / kmW;
  let shapes = "";
  for (const c of CELLS) {
    const cx = px(c.x), cy = py(c.y), r = c.r * k;
    if (cx < -3 * r || cx > W + 3 * r || cy < -3 * r || cy > H + 3 * r) continue;
    const top = 2 + Math.floor(c.level * (COLOURS.length - 2));   // how intense its core gets
    for (let i = 0; i < top; i++) {
      const f = 1 - 0.8 * i / top;
      shapes += `<ellipse cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${(r * f * 1.4).toFixed(1)}" ` +
        `ry="${(r * f).toFixed(1)}" fill="${COLOURS[i]}" transform="rotate(-30 ${cx.toFixed(1)} ${cy.toFixed(1)})"/>`;
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs><filter id="f" x="-10%" y="-10%" width="120%" height="120%">
<feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="3" seed="7"/>
<feDisplacementMap in="SourceGraphic" scale="${(5 * k).toFixed(1)}" xChannelSelector="R" yChannelSelector="G"/>
<feGaussianBlur stdDeviation="0.8"/></filter></defs>
<g filter="url(#f)" opacity="0.75">${shapes}</g></svg>`;
};
