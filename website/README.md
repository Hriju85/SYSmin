# SYSmin Official Landing Page & Web Portal

This directory contains the public marketing website and release portal for **SYSmin (ThrottlerOS)**.

## Features
- **In-Browser Repository Downloader:** Zero-redirect, instant download engine via Blob URLs.
- **Dynamic Platform Instructions:** Step-by-step 1-click guide for Windows (`run.vbs`), Linux (`run.sh`), macOS, and Docker.
- **Interactive Dashboard Guide:** Explains real-time telemetry graphs, dual-panel process segregation, and SJF priority throttling.
- **100% Client-Side Ready:** Can be opened directly in any browser (`file:///`) or hosted on any static edge CDN.

## How to Preview Locally
Simply open [index.html](file:///home/lof85/.gemini/antigravity/scratch/SYSmin/website/index.html) in your browser:
```bash
# On Linux / macOS
open index.html   # or xdg-open index.html

# On Windows
start index.html
```

Or serve with Python:
```bash
python -m http.server 8080 --directory website
```
Then visit `http://localhost:8080`.

## Deployment

### Vercel
1. Set the **Root Directory** in your Vercel Project Settings to `website`.
2. Vercel automatically deploys `index.html` and `style.css` globally to its Edge CDN with zero configuration.
3. Pre-configured headers in `vercel.json` handle clean URLs and asset caching.

### GitHub Pages
1. Go to repository **Settings** -> **Pages**.
2. Select branch `main` and set folder to `/website` (or `/docs`).
3. Click **Save** — the website will be live at `https://<username>.github.io/SYSmin/`.
