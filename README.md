# Hisense TV Price Tracker — Jumia vs Kilimall Kenya

Live price comparison dashboard that auto-scrapes Jumia and Kilimall every morning.

**Live site:** https://YOUR_USERNAME.github.io/hisense-tracker

---

## How it works

```
GitHub Actions (daily 7 AM EAT)
  → runs scraper.py
    → scrapes Jumia Kenya
    → scrapes Kilimall Kenya
  → saves data/hisense.json to repo
GitHub Pages serves index.html
  → index.html fetches data/hisense.json
  → renders live prices
```

## Setup (5 minutes)

### 1. Fork or create this repo on GitHub

### 2. Enable GitHub Pages
- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: **main** / root
- Save — your site will be live at `https://USERNAME.github.io/hisense-tracker`

### 3. Enable GitHub Actions
- Go to **Settings → Actions → General**
- Set "Workflow permissions" to **Read and write permissions**
- Save

### 4. Trigger first scrape manually
- Go to **Actions tab** → "Daily Hisense Price Scrape" → **Run workflow**
- Wait ~2 minutes — it will commit real data to `data/hisense.json`
- Refresh your GitHub Pages URL — you'll see live prices

After that, it runs automatically every day at 7 AM UTC (10 AM Kenya time).

---

## Files

| File | Purpose |
|------|---------|
| `index.html` | Frontend dashboard — reads from `data/hisense.json` |
| `scraper.py` | Python scraper for Jumia + Kilimall |
| `data/hisense.json` | Auto-updated price data (committed by Actions) |
| `.github/workflows/scrape.yml` | GitHub Actions schedule |

## Tech stack
- Python 3.11 · requests · BeautifulSoup4 · fake-useragent
- Vanilla HTML/CSS/JS (no framework)
- GitHub Actions (free tier)
- GitHub Pages (free hosting)
