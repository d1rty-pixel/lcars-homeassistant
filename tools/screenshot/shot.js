// Screenshot an LCARS view in headless Chrome, logged in with a long-lived HA token.
//
// usage: node shot.js <view-path> <width> <height> <out.png> [clip-x clip-y clip-w clip-h]
// env:   HA_TOKEN (required), HA_URL (default http://homeassistant.local:8123), DSF (device scale factor,
//        e.g. 1.1 for 110 % zoom), CHROME (path to chrome.exe / chrome), LCARS_DASHBOARD (default
//        lcars-bridge), SAFE ("top,right,bottom,left" safe-area insets in px, e.g. "0,59,21,59" for an
//        iPhone 16 in landscape: HA pads its views by them)
//
// From WSL, run it with Windows' node.exe so Chrome and node share a machine (puppeteer's pipe and
// debugging port don't cross the WSL boundary), see docs/OPERATIONS.md "Checking layouts".
const puppeteer = require("puppeteer-core");

const [, , view, w, h, out, cx, cy, cw, ch] = process.argv;
const HA = process.env.HA_URL || "http://homeassistant.local:8123";
const PROFILE = require("os").tmpdir() + "/lcars-shot-profile-" + process.pid;

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    // a profile per run, so several shots can run at once
    headless: true, userDataDir: PROFILE,
    args: ["--no-first-run", "--hide-scrollbars"],
  });
  const page = await browser.newPage();
  if (process.env.SAFE) {
    const [t, r, b, l] = process.env.SAFE.split(",");
    await page.evaluateOnNewDocument((t, r, b, l) => {
      const set = () => Object.entries({top: t, right: r, bottom: b, left: l}).forEach(([k, v]) =>
        document.documentElement.style.setProperty(`--app-safe-area-inset-${k}`, `${v}px`));
      if (document.documentElement) set(); else document.addEventListener("DOMContentLoaded", set);
    }, t, r, b, l);
  }
  await page.setViewport({width: +w, height: +h, deviceScaleFactor: process.env.DSF ? +process.env.DSF : 1});
  // HA's frontend reads its auth from localStorage; a long-lived token works as access token
  await page.goto(HA + "/auth/authorize", {waitUntil: "domcontentloaded"});
  await page.evaluate((t, ha) => localStorage.setItem("hassTokens", JSON.stringify({
    access_token: t, token_type: "Bearer", expires_in: 1e9, hassUrl: ha, clientId: ha + "/",
    expires: Date.now() + 1e12, refresh_token: ""})), process.env.HA_TOKEN, HA);
  await page.goto(`${HA}/${process.env.LCARS_DASHBOARD || "lcars-bridge"}/${view}`, {waitUntil: "networkidle2", timeout: 60000});
  await new Promise((r) => setTimeout(r, 8000));   // fonts, LCARdS render passes
  if (process.env.SCROLL) {   // SCROLL=<px>|end: scroll every scrolling element (through shadow roots) and log it
    const log = await page.evaluate((by) => {
      const out = [];
      const walk = (root) => root.querySelectorAll("*").forEach((el) => {
        const oy = getComputedStyle(el).overflowY;
        if ((oy === "auto" || oy === "scroll") && el.scrollHeight > el.clientHeight + 1) {
          el.scrollTop = by === "end" ? el.scrollHeight : +by;
          out.push(`${el.tagName.toLowerCase()}#${el.id} ${el.clientHeight}/${el.scrollHeight} -> ${el.scrollTop}`);
        }
        if (el.shadowRoot) walk(el.shadowRoot);
      });
      walk(document);
      return out;
    }, process.env.SCROLL);
    console.log(log.join("\n") || "nothing scrolls");
    await new Promise((r) => setTimeout(r, 1000));
  }
  await page.screenshot(cx ? {path: out, clip: {x: +cx, y: +cy, width: +cw, height: +ch}} : {path: out});
  await browser.close();
  require("fs").rmSync(PROFILE, {recursive: true, force: true});
})().catch((e) => { console.error(e.message); process.exit(1); });
