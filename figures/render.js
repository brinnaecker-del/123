const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const b = await chromium.launch();
  for (const [f, w, h] of [['fig1', 1210, 696], ['fig2', 1210, 679]]) {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2.5 });
    const svg = fs.readFileSync(`${f}.svg`, 'utf8');
    await p.setContent(`<html><body style="margin:0">${svg}</body></html>`);
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: `${f}.png`, clip: { x: 0, y: 0, width: w, height: h } });
  }
  await b.close();
})();
