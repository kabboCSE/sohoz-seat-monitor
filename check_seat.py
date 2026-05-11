import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import re

load_dotenv()

SEARCH_URL = "https://www.shohoz.com/bus-tickets/booking/bus/search?fromcity=Dhaka&tocity=Lalmonirhat&doj=25-May-2026&dor="
TARGET_OPERATOR = "S.R Travels"

async def check_seats():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading Shohoz search page...")
        await page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
        print("Page loaded.")

        # ── AC Checkbox ───────────────────────────────────────────────
        try:
            await page.get_by_role("checkbox", name="AC", exact=True).check()
            print("AC checkbox selected.")
        except Exception as e:
            print(f"AC checkbox error: {e}")

        await page.wait_for_timeout(2000)

        # ── S.R Travels Operator ──────────────────────────────────────
        try:
            await page.get_by_text("Search Operator").click()
            await page.wait_for_timeout(1000)
            await page.get_by_role("listbox").get_by_text("S.R Travels (Pvt) Ltd").click()
            print("S.R Travels (Pvt) Ltd selected.")
        except Exception as e:
            print(f"Operator select error: {e}")

        await page.wait_for_timeout(3000)
        # await page.screenshot(path="result.png")
        # print("Screenshot saved.")

        # ── Check Seat Count ──────────────────────────────────────────
        found = False
        seat_info = ""
        # await page.pause();

        try:
            content = await page.inner_text("body")
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if TARGET_OPERATOR.lower() in line.lower():
                    nearby = " ".join(lines[max(0, i-2):i+8])
                    print(f"Found operator block: {nearby[:300]}")

                    match = re.search(r'(\d+)\s*[Ss]eat', nearby)
                    if match:
                        seat_count = int(match.group(1))
                        print(f"Seat count: {seat_count}")
                        if seat_count > 0:
                            found = True
                            seat_info = f"{seat_count} seat(s) available"
                    elif "0 Seat" not in nearby and "0 seat" not in nearby:
                        found = True
                        seat_info = nearby[:200]
                    break
            else:
                print(f"{TARGET_OPERATOR} not found on page.")
                print("Page snippet:\n", content[:1000])

        except Exception as e:
            print(f"Parse error: {e}")

        await browser.close()

    if found:
        print("SEATS AVAILABLE! Sending Telegram notification...")
        send_telegram(seat_info)
    else:
        print(f"No seats yet for {TARGET_OPERATOR}.")

def send_telegram(seat_info):
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram secrets missing!")
        return

    message = (
        f"🚌 *SEAT AVAILABLE!*\n\n"
        f"*Route:* Dhaka → Lalmonirhat\n"
        f"*Date:* 25-May-2026\n"
        f"*Operator:* S.R Travels (Pvt) Ltd\n"
        f"*Info:* {seat_info}\n\n"
        f"👉 [Book Now]({SEARCH_URL})"
    )

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
        timeout=15
    )

    if resp.status_code == 200:
        print("Telegram notification sent!")
    else:
        print(f"Telegram error: {resp.text}")

if __name__ == "__main__":
    print("Checking: Dhaka → Lalmonirhat | 25-May-2026")
    print(f"Target: S.R Travels (Pvt) Ltd | AC")
    print("-" * 40)
    asyncio.run(check_seats())
