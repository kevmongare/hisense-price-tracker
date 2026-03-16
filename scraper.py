# scraper.py — runs via GitHub Actions, writes to data/hisense.json
import requests, time, re, json, os
from bs4 import BeautifulSoup
from datetime import datetime, timezone

try:
    from fake_useragent import UserAgent
    UA = UserAgent().random
except Exception:
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "en-KE,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def clean_price(raw):
    """Extract integer price from strings like 'KSh 44,999' or '44999'"""
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None

# ── Jumia scraper ──────────────────────────────────────
def scrape_jumia(query="hisense tv", pages=3):
    results = []
    for page in range(1, pages + 1):
        url = f"https://www.jumia.co.ke/catalog/?q={query.replace(' ','+')}&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("article.prd")
            print(f"  Jumia page {page}: {len(items)} items found")

            for item in items:
                try:
                    name_el  = item.select_one("h3.name")
                    price_el = item.select_one("div.prc")
                    old_el   = item.select_one("div.old")
                    rating_el= item.select_one("div.stars._s")
                    link_el  = item.select_one("a[href]")
                    img_el   = item.select_one("img.img")

                    if not name_el or not price_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if "hisense" not in name.lower():
                        continue

                    results.append({
                        "platform"     : "Jumia",
                        "name"         : name,
                        "price_ksh"    : clean_price(price_el.get_text()),
                        "old_price_ksh": clean_price(old_el.get_text()) if old_el else None,
                        "rating"       : float(rating_el["data-score"]) if rating_el and rating_el.get("data-score") else None,
                        "url"          : "https://www.jumia.co.ke" + link_el["href"] if link_el else None,
                        "image"        : img_el.get("data-src") or img_el.get("src") if img_el else None,
                    })
                except Exception as e:
                    print(f"    Item parse error: {e}")
                    continue

        except Exception as e:
            print(f"  Jumia page {page} failed: {e}")

        time.sleep(1.5)
    return results

# ── Kilimall scraper ───────────────────────────────────
def scrape_kilimall(query="hisense television", pages=3):
    results = []
    for page in range(1, pages + 1):
        url = f"https://www.kilimall.co.ke/search?q={query.replace(' ','+')}&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Kilimall uses several possible selectors — try each
            items = (soup.select("div.product-item") or
                     soup.select("div.goods-item") or
                     soup.select("li.item"))
            print(f"  Kilimall page {page}: {len(items)} items found")

            for item in items:
                try:
                    name_el  = (item.select_one(".product-title") or
                                item.select_one(".goods-name") or
                                item.select_one(".name"))
                    price_el = (item.select_one(".product-price") or
                                item.select_one(".goods-price") or
                                item.select_one(".price"))
                    old_el   = (item.select_one(".original-price") or
                                item.select_one(".market-price"))
                    link_el  = item.select_one("a[href]")
                    img_el   = item.select_one("img")

                    if not name_el or not price_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if "hisense" not in name.lower():
                        continue

                    results.append({
                        "platform"     : "Kilimall",
                        "name"         : name,
                        "price_ksh"    : clean_price(price_el.get_text()),
                        "old_price_ksh": clean_price(old_el.get_text()) if old_el else None,
                        "rating"       : None,
                        "url"          : "https://www.kilimall.co.ke" + link_el["href"] if link_el and link_el["href"].startswith("/") else (link_el["href"] if link_el else None),
                        "image"        : img_el.get("data-src") or img_el.get("src") if img_el else None,
                    })
                except Exception as e:
                    print(f"    Item parse error: {e}")
                    continue

        except Exception as e:
            print(f"  Kilimall page {page} failed: {e}")

        time.sleep(1.2)
    return results

# ── Transform ──────────────────────────────────────────
def transform(records):
    for r in records:
        p, old = r.get("price_ksh"), r.get("old_price_ksh")
        r["discount_pct"] = round((old - p) / old * 100, 1) if old and p and old > p else None
        r["is_best_deal"] = bool(r["discount_pct"] and r["discount_pct"] >= 20)
        # Extract screen size
        m = re.search(r'\b(\d{2})"?\s*(inch)?', r["name"], re.I)
        r["screen_size"] = int(m.group(1)) if m else None
    # Sort best deals first
    return sorted(records, key=lambda x: (not x["is_best_deal"], -(x["discount_pct"] or 0)))

# ── Main ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting scrape...")
    print("\nScraping Jumia...")
    jumia = scrape_jumia()
    print(f"  → {len(jumia)} Hisense listings from Jumia\n")

    print("Scraping Kilimall...")
    kilimall = scrape_kilimall()
    print(f"  → {len(kilimall)} Hisense listings from Kilimall\n")

    all_data = transform(jumia + kilimall)

    output = {
        "scraped_at" : datetime.now(timezone.utc).isoformat(),
        "total"      : len(all_data),
        "jumia_count": len(jumia),
        "kilimall_count": len(kilimall),
        "listings"   : all_data
    }

    os.makedirs("data", exist_ok=True)
    with open("data/hisense.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(all_data)} listings → data/hisense.json")
    print(f"Best deals: {sum(1 for r in all_data if r['is_best_deal'])}")
