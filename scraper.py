"""
scraper.py — Problem 1: Scrape adidas India Men's Footwear

How to run:
  1. Open Chrome: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\chrome_debug"
  2. In that Chrome window, navigate to https://www.adidas.co.in/men-shoes
  3. Wait for products to fully load, then run: python scraper.py
"""

import json, re, csv, time, logging, math
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("scraper.log", encoding="utf-8")],
)
log = logging.getLogger(__name__)

BASE_URL      = "https://www.adidas.co.in"
CATEGORY      = "men-shoes"
REQUEST_DELAY = 2.5
OUTPUT_FILE   = "products_raw.csv"


def parse_next_data(html: str) -> dict | None:
    """
    Extracts the __NEXT_DATA__ JSON block from raw HTML text.

    Next.js embeds all server-rendered page data in a <script id="__NEXT_DATA__">
    tag on every page load. We use a regex to find and parse it directly from the
    raw HTML string — no DOM access needed, which avoids CDP context limitations.
    Returns None if the tag is missing or the JSON is malformed.
    """
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        log.error(f"  JSON decode error: {e}")
        return None


def extract_products(product_list: list) -> list:
    """
    Converts raw product dicts (from the adidas JSON) into clean CSV-ready rows.

    Price logic — each product has a priceData.prices array:
      2 entries -> discounted product:
          type="sale"     -> sale_price (current selling price)
          type="original" -> mrp (the struck-through full price)
      1 entry  -> full-price product:
          sale_price == mrp (both set to the single value)

    Handled explicitly so neither case silently corrupts the other.
    """
    rows = []
    for product in product_list:
        try:
            prices = product.get("priceData", {}).get("prices", [])
            sale_price = mrp = None

            if len(prices) == 2:
                for p in prices:
                    if p.get("type") == "sale":
                        sale_price = p["value"]
                    elif p.get("type") == "original":
                        mrp = p["value"]
            elif len(prices) == 1:
                mrp = sale_price = prices[0]["value"]
            else:
                log.warning(f"Unexpected prices for {product.get('id')}: {prices}")

            url = product.get("url", "")
            if url and not url.startswith("http"):
                url = BASE_URL + url

            rows.append({
                "product_id": product.get("id", ""),
                "name":       product.get("title", ""),
                "sub_brand":  product.get("category", ""),
                "url":        url,
                "sale_price": sale_price,
                "mrp":        mrp,
            })
        except Exception as e:
            log.error(f"Parse error on {product.get('id','?')}: {e}")
    return rows


def fetch_html(page, url: str, timeout_s: int = 25) -> str | None:
    """
    Navigate to a page and capture its HTML document response.

    A response listener is used because DOM access was unreliable in the
    CDP-connected Chrome session. Returns None if capture fails.
    """
    captured = {}

    def handle_response(response):
        try:
            if (response.url.rstrip("/") == url.rstrip("/")
                    and response.request.resource_type == "document"):
                captured["html"] = response.text()
        except Exception:
            pass

    page.on("response", handle_response)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
        deadline = time.time() + 5
        while "html" not in captured and time.time() < deadline:
            time.sleep(0.2)
    except Exception as e:
        log.warning(f"  Navigation error: {e}")
    finally:
        page.remove_listener("response", handle_response)

    return captured.get("html")


def fetch_page_products(page, url: str) -> list:
    """Fetches one paginated category page and returns its product list ([] on failure)."""
    html = fetch_html(page, url)
    if not html:
        return []
    data = parse_next_data(html)
    if not data:
        return []
    return data.get("props", {}).get("pageProps", {}).get("products", [])


def save_to_csv(rows: list, filename: str):
    """Writes the list of product dicts to a CSV file with a fixed column order."""
    if not rows:
        log.error("Nothing to save.")
        return
    fieldnames = ["product_id", "name", "sub_brand", "url", "sale_price", "mrp"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    log.info(f"✓ {len(rows)} rows → {filename}")


def get_adidas_tab(pw):
    """
    Connects to the user's already-running Chrome via CDP and returns the open
    adidas.co.in tab. Chrome must have been started with --remote-debugging-port=9222.
    Returns None if no adidas tab is found.
    """
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    for context in browser.contexts:
        for page in context.pages:
            if "adidas.co.in" in page.url:
                return page

    return None


def main():
    log.info("=== Adidas Scraper — Starting ===")

    with sync_playwright() as pw:
        try:
            page = get_adidas_tab(pw)
        except Exception as e:
            log.error(
                f"Cannot connect to Chrome: {e}\n"
                'Run: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\chrome_debug"\n'
                "Then open https://www.adidas.co.in/men-shoes in that window."
            )
            return

        if not page:
            log.error("No adidas tab found. Open the men-shoes page in the CDP Chrome window first.")
            return

        log.info(f"✓ Connected. Using tab: {page.url}")
        page.bring_to_front()

        # ── Page 1: fetch and discover pagination info ──
        first_url = f"{BASE_URL}/{CATEGORY}"
        html = fetch_html(page, first_url)
        data = parse_next_data(html) if html else None
        if not data:
            log.error("Could not load/parse page 1. Is the CDP Chrome tab still open on adidas?")
            return

        info        = data["props"]["pageProps"]["info"]
        total_count = info["count"]     # discovered dynamically, never hardcoded
        view_size   = info["viewSize"]  # products per page (48)
        products    = data["props"]["pageProps"].get("products", [])

        total_pages = math.ceil(total_count / view_size)

        log.info(
            f"Total: {total_count} products, "
            f"{view_size}/page → {total_pages} pages"
        )
        all_rows = extract_products(products)

        # ── Remaining pages: increment ?start= until full catalogue is covered ──
        start, page_num = view_size, 2
        while start < total_count:
            log.info(f"Page {page_num} (start={start})...")
            page_products = fetch_page_products(page, f"{BASE_URL}/{CATEGORY}?start={start}")

            if not page_products:
                log.warning("  No products returned — skipping/ending.")
                if start + view_size >= total_count:
                    break
            else:
                all_rows.extend(extract_products(page_products))
                log.info(f"  → {len(page_products)} products (running total: {len(all_rows)})")

            time.sleep(REQUEST_DELAY)
            start += view_size
            page_num += 1

    log.info(f"Grand total: {len(all_rows)} / {total_count} expected.")
    save_to_csv(all_rows, OUTPUT_FILE)
    log.info("=== Done ===")


if __name__ == "__main__":
    main()
