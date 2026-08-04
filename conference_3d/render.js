#!/usr/bin/env node
/**
 * Render conference 3D scene from multiple camera angles.
 */
import puppeteer from 'puppeteer';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import http from 'http';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = path.join(__dirname, 'output');
const PORT = 8765;

const ANGLES = [
  { name: 'angle1_front_overview', preset: 'front', desc: '正面全景 - 从会场后方看向舞台' },
  { name: 'angle2_side_panorama', preset: 'side', desc: '侧面全景 - 从侧面俯瞰会场' },
  { name: 'angle3_stage_view', preset: 'stage', desc: '舞台视角 - 从舞台看向参会者' },
];

const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
};

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let filePath = path.join(__dirname, req.url === '/' ? 'scene.html' : req.url.split('?')[0]);
      if (!filePath.startsWith(__dirname)) {
        res.writeHead(403); res.end(); return;
      }
      if (!fs.existsSync(filePath)) {
        res.writeHead(404); res.end('Not found'); return;
      }
      const ext = path.extname(filePath);
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      fs.createReadStream(filePath).pipe(res);
    });
    server.listen(PORT, () => resolve(server));
  });
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const server = await startServer();
  const sceneUrl = `http://localhost:${PORT}/scene.html?w=1920&h=1080`;

  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--enable-webgl',
      '--ignore-gpu-blocklist',
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  page.on('pageerror', err => console.error('PAGE ERROR:', err.message));

  console.log('Loading 3D scene...');
  await page.goto(sceneUrl, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.waitForFunction(() => window.sceneReady === true, { timeout: 15000 });

  const results = [];
  for (const angle of ANGLES) {
    console.log(`Rendering: ${angle.desc}...`);
    await page.evaluate((preset) => window.render(preset), angle.preset);
    await new Promise(r => setTimeout(r, 800));

    const outPath = path.join(OUTPUT_DIR, `${angle.name}.png`);
    await page.screenshot({ path: outPath, type: 'png' });
    results.push({ ...angle, path: outPath });
    console.log(`  Saved: ${outPath}`);
  }

  await browser.close();
  server.close();

  console.log('\n=== Render complete ===');
  results.forEach(r => console.log(`  ${r.desc}: ${r.path}`));
}

main().catch(err => {
  console.error('Render failed:', err);
  process.exit(1);
});
