// Screenshot an LCARS view in headless Chrome, logged in with a long-lived HA token.
//
// usage: node shot.js <view-path> <width> <height> <out.png> [clip-x clip-y clip-w clip-h]
// env:   HA_TOKEN (required), HA_URL (default http://homeassistant.local:8123), DSF (device scale factor,
//        e.g. 1.1 for 110 % zoom), CHROME (path to chrome.exe / chrome)
//
// From WSL, run it with Windows' node.exe so Chrome and node share a machine (puppeteer's pipe and
// debugging port don't cross the WSL boundary), see docs/OPERATIONS.md "Checking layouts".
const puppeteer = require("puppeteer-core");

const [, , view, w, h, out, cx, cy, cw, ch] = process.argv;
const HA = process.env.HA_URL || "http://homeassistant.local:8123";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true, userDataDir: require("os").tmpdir() + "/lcars-shot-profile",
    args: ["--no-first-run", "--hide-scrollbars"],
  });
  const page = await browser.newPage();
  await page.setViewport({width: +w, height: +h, deviceScaleFactor: process.env.DSF ? +process.env.DSF : 1});
  // HA's frontend reads its auth from localStorage; a long-lived token works as access token
  await page.goto(HA + "/auth/authorize", {waitUntil: "domcontentloaded"});
  await page.evaluate((t, ha) => localStorage.setItem("hassTokens", JSON.stringify({
    access_token: t, token_type: "Bearer", expires_in: 1e9, hassUrl: ha, clientId: ha + "/",
    expires: Date.now() + 1e12, refresh_token: ""})), process.env.HA_TOKEN, HA);
  await page.goto(`${HA}/lcars-bridge/${view}`, {waitUntil: "networkidle2", timeout: 60000});
  await new Promise((r) => setTimeout(r, 8000));   // fonts, LCARdS render passes
  await page.screenshot(cx ? {path: out, clip: {x: +cx, y: +cy, width: +cw, height: +ch}} : {path: out});
  await browser.close();
})().catch((e) => { console.error(e.message); process.exit(1); });
