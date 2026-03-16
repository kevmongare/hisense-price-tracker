# scraper.py — Jumia vs Kilimall Hisense TV price scraper
# Handles bot-blocking with rotating headers + graceful seed fallback

import requests, time, re, json, os
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# ── User-agent rotation (no fake_useragent dependency needed) ──
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

import random
random.seed()

def get_headers():
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-KE,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

def clean_price(raw):
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None

# ── Optional: ScraperAPI proxy (free 1000 calls/month) ──
# Sign up free at scraperapi.com, paste your key here or set env var
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

def make_url(target_url):
    """Wrap URL with ScraperAPI if key is available, else use direct."""
    if SCRAPER_API_KEY:
        return f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={target_url}&country_code=ke"
    return target_url

# ── Jumia scraper ──────────────────────────────────────────
def scrape_jumia(query="hisense tv", pages=3):
    results = []
    session = requests.Session()

    # Warm up session with homepage first (helps avoid bot detection)
    try:
        session.get("https://www.jumia.co.ke", headers=get_headers(), timeout=10)
        time.sleep(2)
    except Exception:
        pass

    for page in range(1, pages + 1):
        target = f"https://www.jumia.co.ke/catalog/?q={query.replace(' ', '+')}&page={page}"
        url = make_url(target)
        try:
            resp = session.get(url, headers=get_headers(), timeout=20)
            print(f"  Jumia page {page}: HTTP {resp.status_code}")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select("article.prd")
                print(f"  Jumia page {page}: {len(items)} product cards found")

                for item in items:
                    try:
                        name_el  = item.select_one("h3.name")
                        price_el = item.select_one("div.prc")
                        old_el   = item.select_one("div.old")
                        rating_el= item.select_one("div.stars._s")
                        link_el  = item.select_one("a[href]")

                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if "hisense" not in name.lower():
                            continue

                        results.append({
                            "platform"      : "Jumia",
                            "name"          : name,
                            "price_ksh"     : clean_price(price_el.get_text()),
                            "old_price_ksh" : clean_price(old_el.get_text()) if old_el else None,
                            "rating"        : float(rating_el["data-score"]) if rating_el and rating_el.get("data-score") else None,
                            "url"           : "https://www.jumia.co.ke" + link_el["href"] if link_el else None,
                            "image"         : None,
                        })
                    except Exception as e:
                        print(f"    Parse error: {e}")

            elif resp.status_code == 403:
                print(f"  Jumia page {page}: 403 Forbidden — blocked. Add SCRAPER_API_KEY secret to fix.")

        except Exception as e:
            print(f"  Jumia page {page} failed: {e}")

        time.sleep(random.uniform(2.0, 4.0))

    print(f"  Jumia total: {len(results)} Hisense listings")
    return results

# ── Kilimall scraper ───────────────────────────────────────
def scrape_kilimall(query="hisense television", pages=3):
    results = []
    session = requests.Session()

    try:
        session.get("https://www.kilimall.co.ke", headers=get_headers(), timeout=10)
        time.sleep(2)
    except Exception:
        pass

    for page in range(1, pages + 1):
        target = f"https://www.kilimall.co.ke/search?q={query.replace(' ', '+')}&page={page}"
        url = make_url(target)
        try:
            resp = session.get(url, headers=get_headers(), timeout=20)
            print(f"  Kilimall page {page}: HTTP {resp.status_code}")

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")

                items = (soup.select("div.product-item") or
                         soup.select("div.goods-item")   or
                         soup.select("li.item")          or
                         soup.select("div[class*='product']"))
                print(f"  Kilimall page {page}: {len(items)} product cards found")

                for item in items:
                    try:
                        name_el  = (item.select_one(".product-title") or
                                    item.select_one(".goods-name")    or
                                    item.select_one(".name"))
                        price_el = (item.select_one(".product-price") or
                                    item.select_one(".goods-price")   or
                                    item.select_one(".price"))
                        old_el   = (item.select_one(".original-price") or
                                    item.select_one(".market-price"))
                        link_el  = item.select_one("a[href]")

                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        if "hisense" not in name.lower():
                            continue

                        href = link_el["href"] if link_el else None
                        full_url = ("https://www.kilimall.co.ke" + href
                                    if href and href.startswith("/") else href)

                        results.append({
                            "platform"      : "Kilimall",
                            "name"          : name,
                            "price_ksh"     : clean_price(price_el.get_text()),
                            "old_price_ksh" : clean_price(old_el.get_text()) if old_el else None,
                            "rating"        : None,
                            "url"           : full_url,
                            "image"         : None,
                        })
                    except Exception as e:
                        print(f"    Parse error: {e}")

            elif resp.status_code == 403:
                print(f"  Kilimall page {page}: 403 Forbidden — blocked.")

        except Exception as e:
            print(f"  Kilimall page {page} failed: {e}")

        time.sleep(random.uniform(1.5, 3.0))

    print(f"  Kilimall total: {len(results)} Hisense listings")
    return results

# ── Transform ──────────────────────────────────────────────
def transform(records):
    for r in records:
        p, old = r.get("price_ksh"), r.get("old_price_ksh")
        r["discount_pct"] = round((old - p) / old * 100, 1) if old and p and old > p else None
        r["is_best_deal"] = bool(r["discount_pct"] and r["discount_pct"] >= 20)
        m = re.search(r'\b(\d{2})"?\s*(inch)?', r["name"], re.I)
        r["screen_size"] = int(m.group(1)) if m else None
    return sorted(records, key=lambda x: (not x["is_best_deal"], -(x["discount_pct"] or 0)))

# ── Seed data fallback (shown when scraping is blocked) ────
SEED_LISTINGS = [
    {"platform":"Jumia",    "name":"Hisense 32A4G HD Ready Smart TV","price_ksh":21999,"old_price_ksh":26999,"rating":4.3,"discount_pct":18.5,"is_best_deal":False,"screen_size":32,"url":"https://www.jumia.co.ke/catalog/?q=hisense+tv","image":None},
    {"platform":"Kilimall", "name":"Hisense 32A4K Smart TV",         "price_ksh":18999,"old_price_ksh":22000,"rating":None,"discount_pct":13.6,"is_best_deal":False,"screen_size":32,"url":"https://www.kilimall.co.ke/search?q=hisense+tv","image":None},
    {"platform":"Jumia",    "name":"Hisense 43A5800FW FHD Android TV","price_ksh":34999,"old_price_ksh":42000,"rating":4.5,"discount_pct":16.7,"is_best_deal":False,"screen_size":43,"url":"https://www.jumia.co.ke/catalog/?q=hisense+tv","image":None},
    {"platform":"Kilimall", "name":"Hisense 43E57KQ QLED 4K Google TV","price_ksh":38500,"old_price_ksh":44000,"rating":None,"discount_pct":12.5,"is_best_deal":False,"screen_size":43,"url":"https://www.kilimall.co.ke/search?q=hisense+tv","image":None},
    {"platform":"Jumia",    "name":"Hisense 55A7200F 4K UHD Smart TV","price_ksh":44999,"old_price_ksh":62500,"rating":4.6,"discount_pct":28.0,"is_best_deal":True, "screen_size":55,"url":"https://www.jumia.co.ke/catalog/?q=hisense+tv","image":None},
    {"platform":"Kilimall", "name":"Hisense 55A7200F 4K UHD",        "price_ksh":51000,"old_price_ksh":None, "rating":None,"discount_pct":None,"is_best_deal":False,"screen_size":55,"url":"https://www.kilimall.co.ke/search?q=hisense+tv","image":None},
    {"platform":"Jumia",    "name":"Hisense 55E7KQ Pro QLED MiniLED","price_ksh":74999,"old_price_ksh":95000,"rating":4.8,"discount_pct":21.1,"is_best_deal":True, "screen_size":55,"url":"https://www.jumia.co.ke/catalog/?q=hisense+tv","image":None},
    {"platform":"Kilimall", "name":"Hisense 55E7KQ QLED TV",         "price_ksh":79500,"old_price_ksh":90000,"rating":None,"discount_pct":11.7,"is_best_deal":False,"screen_size":55,"url":"https://www.kilimall.co.ke/search?q=hisense+tv","image":None},
    {"platform":"Jumia",    "name":"Hisense 65U7H ULED 4K 144Hz",    "price_ksh":84999,"old_price_ksh":110000,"rating":4.7,"discount_pct":22.7,"is_best_deal":True, "screen_size":65,"url":"https://www.jumia.co.ke/catalog/?q=hisense+tv","image":None},
    {"platform":"Kilimall", "name":"Hisense 65U7H ULED TV",          "price_ksh":91000,"old_price_ksh":105000,"rating":None,"discount_pct":13.3,"is_best_deal":False,"screen_size":65,"url":"https://www.kilimall.co.ke/search?q=hisense+tv","image":None},
]

# ── Main pipeline ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("Hisense TV Price Scraper — starting")
    print("=" * 50)

    if SCRAPER_API_KEY:
        print(f"ScraperAPI key found — using proxy routing\n")
    else:
        print("No SCRAPER_API_KEY found — trying direct (may be blocked by platforms)\n")

    print("Scraping Jumia...")
    jumia = scrape_jumia()

    print("\nScraping Kilimall...")
    kilimall = scrape_kilimall()

    all_scraped = jumia + kilimall

    if len(all_scraped) == 0:
        # Platforms blocked the scraper — keep existing data, just update timestamp
        print("\nWARNING: 0 listings scraped — platforms likely blocked the request.")
        print("Loading existing data/hisense.json and refreshing timestamp only...")

        try:
            with open("data/hisense.json") as f:
                existing = json.load(f)
            listings = existing.get("listings", SEED_LISTINGS)
            note = "Platforms blocked live scrape — showing last known prices. Add SCRAPER_API_KEY secret for reliable data."
        except Exception:
            listings = SEED_LISTINGS
            note = "Seed data — add SCRAPER_API_KEY GitHub secret to enable live scraping."

        output = {
            "scraped_at"      : datetime.now(timezone.utc).isoformat(),
            "total"           : len(listings),
            "jumia_count"     : sum(1 for l in listings if l["platform"] == "Jumia"),
            "kilimall_count"  : sum(1 for l in listings if l["platform"] == "Kilimall"),
            "live_scrape"     : False,
            "note"            : note,
            "listings"        : listings,
        }
    else:
        listings = transform(all_scraped)
        output = {
            "scraped_at"     : datetime.now(timezone.utc).isoformat(),
            "total"          : len(listings),
            "jumia_count"    : len(jumia),
            "kilimall_count" : len(kilimall),
            "live_scrape"    : True,
            "note"           : "",
            "listings"       : listings,
        }
        print(f"\nLive scrape successful — {len(listings)} listings")

    os.makedirs("data", exist_ok=True)
    with open("data/hisense.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved → data/hisense.json")
    print(f"Total  : {output['total']} listings")
    print(f"Live   : {output['live_scrape']}")
    print("=" * 50)
