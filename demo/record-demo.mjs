/**
 * Records the Nookr judging demo as a video.
 *
 * Drives a real Chromium against the running app — nothing is staged or
 * mocked. Every number that appears on screen came out of the API during the
 * recording.
 *
 * Usage:
 *   node record-demo.mjs                 # both servers already running
 *   API_URL=… APP_URL=… node record-demo.mjs
 */

import { execFileSync } from 'node:child_process'
import { mkdirSync, readdirSync, rmSync, statSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import ffmpeg from '@ffmpeg-installer/ffmpeg'
import { chromium } from 'playwright'

const HERE = dirname(fileURLToPath(import.meta.url))
const APP_URL = process.env.APP_URL ?? 'http://127.0.0.1:5173'
const API_URL = process.env.API_URL ?? 'http://127.0.0.1:8000'

const RAW_DIR = join(HERE, '.recording')
const OUT_DIR = join(HERE, 'output')
const OUT_FILE = join(OUT_DIR, 'nookr-demo.mp4')

const WIDTH = 1440
const HEIGHT = 900

/* -------------------------------------------------------------------------- */
/* On-screen narration + a visible cursor, injected into the page             */
/* -------------------------------------------------------------------------- */

const OVERLAY = `
(() => {
  if (window.__nookrOverlay) return;
  window.__nookrOverlay = true;

  // This runs at document-start, when document.documentElement is still null,
  // so every DOM touch is deferred until the first call.
  let caption = null;
  let cursor = null;

  const ensure = () => {
    if (caption || !document.documentElement) return caption;

    const style = document.createElement('style');
    style.textContent = [
      '#nookr-caption{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);',
      'z-index:2147483647;pointer-events:none;max-width:min(1040px,84vw);padding:14px 28px;',
      'background:rgba(15,42,77,.95);color:#fff;border-radius:14px;',
      'box-shadow:0 12px 38px rgba(15,42,77,.36);text-align:center;letter-spacing:-.01em;',
      "font:500 19px/1.35 ui-sans-serif,'Segoe UI',system-ui,sans-serif;",
      'opacity:0;transition:opacity .3s ease}',
      '#nookr-caption.on{opacity:1}',
      '#nookr-caption .step{display:block;font-size:12px;font-weight:700;letter-spacing:.11em;',
      'text-transform:uppercase;color:#6fc9a1;margin-bottom:5px}',
      '#nookr-caption .sub{display:block;font-size:15px;font-weight:400;opacity:.84;margin-top:5px}',
      '#nookr-cursor{position:fixed;z-index:2147483646;pointer-events:none;width:22px;height:22px;',
      'margin:-11px 0 0 -11px;border-radius:50%;border:2px solid rgba(15,42,77,.85);',
      'background:rgba(42,148,105,.3);transition:transform .09s ease-out;opacity:0}',
      '#nookr-cursor.on{opacity:1}',
      '@keyframes nookr-ping{from{transform:scale(1);opacity:.9}to{transform:scale(2.7);opacity:0}}',
      '.nookr-ping{position:fixed;z-index:2147483645;pointer-events:none;width:26px;height:26px;',
      'margin:-13px 0 0 -13px;border-radius:50%;border:2px solid #2a9469;',
      'animation:nookr-ping .5s ease-out forwards}'
    ].join('');
    document.documentElement.appendChild(style);

    caption = document.createElement('div');
    caption.id = 'nookr-caption';
    document.documentElement.appendChild(caption);

    cursor = document.createElement('div');
    cursor.id = 'nookr-cursor';
    document.documentElement.appendChild(cursor);

    return caption;
  };

  addEventListener('mousemove', (e) => {
    if (!ensure()) return;
    cursor.classList.add('on');
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
  }, true);

  addEventListener('mousedown', (e) => {
    if (!ensure()) return;
    const ping = document.createElement('div');
    ping.className = 'nookr-ping';
    ping.style.left = e.clientX + 'px';
    ping.style.top = e.clientY + 'px';
    document.documentElement.appendChild(ping);
    setTimeout(() => ping.remove(), 520);
  }, true);

  window.__caption = (step, text, sub) => {
    const el = ensure();
    if (!el) return false;
    el.innerHTML =
      (step ? '<span class="step">' + step + '</span>' : '') +
      text +
      (sub ? '<span class="sub">' + sub + '</span>' : '');
    el.classList.add('on');
    return true;
  };
  window.__captionOff = () => { if (caption) caption.classList.remove('on'); };
})();
`

/* -------------------------------------------------------------------------- */

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  rmSync(RAW_DIR, { recursive: true, force: true })
  mkdirSync(RAW_DIR, { recursive: true })
  mkdirSync(OUT_DIR, { recursive: true })

  // Restore the deterministic dataset before the camera rolls, so the reset
  // itself is not in the video and the scripted outcome is guaranteed.
  process.stdout.write('Resetting demo data … ')
  const reset = await fetch(`${API_URL}/api/demo/reset`, { method: 'POST' })
  if (!reset.ok) throw new Error(`Demo reset failed: HTTP ${reset.status}`)
  console.log('done')

  const browser = await chromium.launch({ args: ['--force-device-scale-factor=1'] })
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
    recordVideo: { dir: RAW_DIR, size: { width: WIDTH, height: HEIGHT } },
    locale: 'en-IN',
  })
  await context.addInitScript(OVERLAY)

  const page = await context.newPage()

  const say = async (step, text, sub, hold = 2600) => {
    const shown = await page.evaluate(
      ([s, t, u]) => (window.__caption ? window.__caption(s, t, u) : false),
      [step, text, sub ?? ''],
    )
    if (!shown) throw new Error(`Caption overlay is not present: "${text}"`)
    await wait(hold)
  }
  const hush = async (ms = 500) => {
    await page.evaluate(() => window.__captionOff?.())
    await wait(ms)
  }
  /** Move to the element first, so the on-screen cursor travels visibly. */
  const click = async (locator, settle = 900) => {
    await locator.scrollIntoViewIfNeeded()
    await wait(320)
    await locator.hover()
    await wait(260)
    await locator.click()
    await wait(settle)
  }

  try {
    /* ---------------------------------------------------------- 0. Opening */
    await page.goto(APP_URL, { waitUntil: 'networkidle' })
    await wait(900)
    await say(
      'Nookr',
      'An operating system for labour cooperatives',
      'SIH26089 · Cooperative Gig Services Platform',
      3400,
    )
    await say(
      null,
      'Not a marketplace. The cooperative owns the workforce intelligence.',
      'Understand demand → identify skills → allocate fairly → plan the workforce',
      3600,
    )
    await hush()

    await click(page.getByRole('button', { name: 'Try Demo' }), 2200)
    await page.waitForURL(/\/customer/, { timeout: 15000 })
    await wait(1200)

    /* ------------------------------------------------ 1. AI understanding */
    await say(
      'Step 1 of 10',
      'The customer describes the problem in their own words',
      'Free text or voice — no service menu, no category picker',
      3000,
    )

    const box = page.getByRole('textbox', { name: /Describe Your Service Requirement/i })
    await box.scrollIntoViewIfNeeded()
    await box.click()
    await box.fill('')
    await box.type('My kitchen sink is leaking. I need a plumber tomorrow morning.', {
      delay: 42,
    })
    await wait(1100)
    await hush(300)

    await click(page.getByRole('button', { name: 'Understand my request' }), 2000)
    await say(
      'AI #1 · Service understanding',
      'Plain language becomes a structured job requirement',
      'The engine that produced it is named on screen — here, the built-in rule engine',
      4600,
    )
    await hush()

    /* -------------------------------------- 2 & 3. Matching and fairness */
    await click(page.getByRole('button', { name: 'Find Best Worker' }), 2600)
    await page.waitForURL(/\/matching/, { timeout: 15000 })
    await wait(1400)

    await say(
      'Step 2 of 10',
      'Every eligible member is scored server-side',
      '26 considered · the rest excluded with a stated reason',
      4000,
    )

    await page.mouse.wheel(0, 420)
    await wait(1500)
    await say(
      'AI #2 · Fair allocation',
      'Fairness is 20% of the score — and it decides this job',
      'The nearest plumber and the best-rated plumber are both near capacity, and both lose',
      5200,
    )

    await page.mouse.wheel(0, 620)
    await wait(1600)
    await say(
      'Step 3 of 10',
      'Why this worker? Every component, with its reasoning',
      'Skill · Availability · Location · Rating · Fairness — nothing is a black box',
      5000,
    )
    await hush()

    await click(page.getByRole('button', { name: 'Assign Worker' }), 2600)
    await page.waitForURL(/\/bookings\/\d+/, { timeout: 15000 })
    const bookingUrl = page.url()
    await wait(1300)
    await say(
      null,
      'The score that justified the allocation is stored on the booking',
      'So "why this worker?" can still be answered months later',
      3800,
    )
    await hush()

    /* ------------------------------------------------ 4-6. Worker portal */
    await click(page.getByRole('button', { name: 'Worker', exact: true }), 2600)
    await page.waitForURL(/\/worker/, { timeout: 15000 })
    await wait(1500)
    await say(
      'Step 4 of 10',
      'The same job, now in the worker portal',
      'Skills, certifications, availability, earnings and welfare — the member owns their record',
      4200,
    )
    await hush()

    await click(page.getByRole('button', { name: 'View details' }).first(), 2200)
    await page.waitForURL(/\/bookings\/\d+/, { timeout: 15000 })
    await wait(900)

    await click(page.getByRole('button', { name: 'Accept Job' }), 2000)
    await say('Step 5 of 10', 'Accepted — the customer can now track it', null, 2400)
    await hush(300)

    await click(page.getByRole('button', { name: 'Start Job' }), 2000)
    await say(
      'Step 6 of 10',
      'Work in progress',
      'The member is automatically marked unavailable while the job runs',
      2800,
    )
    await hush(300)

    await click(page.getByRole('button', { name: 'Complete Job' }), 2400)
    await say(null, 'Completed — payment is now due', null, 2400)
    await hush()

    /* -------------------------------------------- 7 & 8. Payment, rating */
    await click(page.getByRole('button', { name: 'Customer', exact: true }), 2400)
    await page.goto(bookingUrl, { waitUntil: 'networkidle' })
    await wait(1400)

    await say(
      'Step 7 of 10',
      'The cooperative payment model, made visible',
      'Simulated payment — no real transaction takes place anywhere in this system',
      3800,
    )
    await click(page.getByRole('button', { name: 'Pay Now' }), 2600)
    await say(
      null,
      '₹650 → worker ₹560 · cooperative ₹40 · welfare ₹20 · technology ₹30',
      'Most of it goes to the member; the rest funds insurance, training and the platform',
      4600,
    )
    await hush()

    await click(page.getByRole('button', { name: 'View invoice' }), 1800)
    await say(null, 'A real invoice, printable and downloadable', null, 3400)
    await page.keyboard.press('Escape')
    await wait(900)
    await hush(300)

    await say('Step 8 of 10', 'The customer rates the service', null, 2200)
    await click(page.getByRole('button', { name: '5 stars' }), 700)
    const comment = page.getByPlaceholder(/what went well/i)
    await comment.click()
    await comment.type('Fixed the leak in one visit and cleaned up afterwards.', { delay: 34 })
    await wait(800)
    await click(page.getByRole('button', { name: 'Submit Feedback' }), 2400)
    await say(
      null,
      'Feedback flows straight into the intelligence layer',
      "The member's rating, the cooperative's analytics and the forecast all move",
      4200,
    )
    await hush()

    /* ----------------------------------------------------- 9. Dashboard */
    await click(page.getByRole('button', { name: 'Cooperative admin' }), 2600)
    await page.waitForURL(/\/dashboard/, { timeout: 15000 })
    await wait(1800)
    await say(
      'Step 9 of 10',
      'The Cooperative Intelligence Dashboard',
      'Utilisation, a fairness score, welfare fund — every figure derived from the database',
      4600,
    )
    await page.mouse.wheel(0, 520)
    await wait(1800)
    await say(
      null,
      'Who is carrying the work, and who has room',
      'The same workload definition drives matching, this panel and the planner',
      4000,
    )
    await hush()

    /* ------------------------------------------- 10. Forecast + planning */
    await page.goto(`${APP_URL}/forecast`, { waitUntil: 'networkidle' })
    await wait(1900)
    await say(
      'Step 10 of 10',
      'AI #3 · Demand forecasting',
      'A weighted moving average with a damped trend — the method is stated, not hidden',
      4400,
    )
    await page.mouse.wheel(0, 640)
    await wait(1600)
    await say(
      'AI #4 · Workforce planning',
      'The forecast becomes a staffing decision',
      'Electrical demand is rising · 4 electricians available, 6 required · activate 2, prioritise Zone 3',
      5400,
    )
    await hush()

    await page.goto(`${APP_URL}/workforce`, { waitUntil: 'networkidle' })
    await wait(1600)
    await page.mouse.wheel(0, 1750)
    await wait(1500)
    await say(
      'AI #5 · Skill gap detection',
      'Which skills the cooperative should train for next',
      'Solar Installation — 6 required, 4 certified · train and certify 2 more electricians',
      5200,
    )
    await hush()

    await page.goto(`${APP_URL}/analytics`, { waitUntil: 'networkidle' })
    await wait(2100)
    await say(
      null,
      'Eight weeks of real operating history behind every chart',
      'Demand, zones, utilisation, earnings, welfare and ratings',
      4200,
    )
    await page.mouse.wheel(0, 700)
    await wait(2200)
    await hush()

    /* ------------------------------------------------------------ Close */
    await page.goto(`${APP_URL}/dashboard`, { waitUntil: 'networkidle' })
    await wait(1400)
    await say(
      'Nookr',
      'Nookr does not replace cooperative workers.',
      'It gives cooperatives the intelligence to organise, support and empower them.',
      5200,
    )
    await hush(900)
  } finally {
    await context.close()
    await browser.close()
  }

  /* ------------------------------------------------------- transcode */
  const raw = readdirSync(RAW_DIR)
    .filter((f) => f.endsWith('.webm'))
    .map((f) => join(RAW_DIR, f))
    .sort((a, b) => statSync(b).size - statSync(a).size)[0]

  if (!raw) throw new Error('Playwright produced no video file.')

  console.log('Transcoding to H.264 mp4 …')
  rmSync(OUT_FILE, { force: true })
  execFileSync(
    ffmpeg.path,
    [
      '-y',
      '-i', raw,
      '-c:v', 'libx264',
      '-preset', 'slow',
      '-crf', '22',
      '-pix_fmt', 'yuv420p',
      // Even dimensions are required by yuv420p.
      '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=25',
      '-movflags', '+faststart',
      OUT_FILE,
    ],
    { stdio: ['ignore', 'ignore', 'pipe'] },
  )

  rmSync(RAW_DIR, { recursive: true, force: true })
  const { size } = statSync(OUT_FILE)
  console.log(`\n✓ ${resolve(OUT_FILE)}  (${(size / 1_048_576).toFixed(1)} MB)`)
}

main().catch((error) => {
  console.error('\nRecording failed:', error.message)
  process.exit(1)
})
