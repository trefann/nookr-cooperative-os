# Demo recorder

Records the ten-step Nookr judging demo as an mp4, by driving a real Chromium
against the running application. Nothing is staged: every figure that appears
on screen came out of the API during the recording.

## Usage

Start both servers first (see the root `README.md`), then:

```bash
cd demo
```

```bash
npm install
```

```bash
npx playwright install chromium
```

```bash
npm run record
```

The result lands at `demo/output/nookr-demo.mp4` — 1440x900, H.264, roughly
three and a quarter minutes.

Point it at other hosts with environment variables:

```bash
APP_URL=https://nookr.vercel.app API_URL=https://nookr-api.onrender.com npm run record
```

## What it does

1. Calls `POST /api/demo/reset` **before** recording starts, so the dataset is
   the deterministic one and the reset itself is not in the video.
2. Injects a caption overlay and a visible cursor into the page, so the
   recording is followable without a voiceover. The script aborts if the
   overlay fails to inject, rather than silently producing a caption-free file.
3. Walks the full journey: AI understanding → matching → fair allocation →
   worker accepts, starts, completes → payment and invoice → rating →
   dashboard → forecast → workforce planning → skill gaps → analytics.
4. Transcodes Playwright's VP8/webm output to H.264 mp4 with a bundled static
   ffmpeg, so no system ffmpeg is required.

Timings live at the call sites (`say(...)` holds a caption; `click(...)` moves
the cursor before clicking), so pacing is easy to adjust.
