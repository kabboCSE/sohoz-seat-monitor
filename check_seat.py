import requests
import os
import json

# ========== CONFIG ==========
FROM_CITY = "Dhaka"
TO_CITY = "Lalmonirhat"
DATE = "25-May-2026"
TARGET_OPERATOR = "S.R Travels"
# ============================

LOGIN_URL = "https://webapi.shohoz.com/v1.0/web/user/login"
SEARCH_URL = f"https://webapi.shohoz.com/v1.0/web/booking/bus/search-trips?from_city={FROM_CITY}&to_city={TO_CITY}&date_of_journey={DATE}&dor="

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.shohoz.com/",
}

def get_token():
    email = os.environ.get("SHOHOZ_EMAIL")
    password = os.environ.get("SHOHOZ_PASSWORD")

    if not email or not password:
        raise Exception("SHOHOZ_EMAIL or SHOHOZ_PASSWORD secret missing!")

    payload = {"email": email, "password": password}
    resp = requests.post(LOGIN_URL, json=payload, headers=HEADERS, timeout=30)
    data = resp.json()

    # Try common token fields
    token = (
        data.get("data", {}).get("token")
        or data.get("token")
        or data.get("access_token")
        or data.get("data", {}).get("access_token")
    )

    if not token:
        print(f"Login response: {json.dumps(data, indent=2)[:500]}")
        raise Exception("Could not extract token from login response!")

    print("Login successful, token obtained.")
    return token

def check_seats(token):
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    resp = requests.get(SEARCH_URL, headers=headers, timeout=30)

    if resp.status_code != 200:
        print(f"API error: {resp.status_code} - {resp.text[:300]}")
        return False, ""

    data = resp.json()

    # Navigate to trips list
    trips = (
        data.get("data", {}).get("buses")
        or data.get("data", {}).get("trips")
        or data.get("buses")
        or data.get("trips")
        or []
    )

    if not trips:
        print(f"No trips found. Response keys: {list(data.keys())}")
        print(f"Full response (first 500 chars): {json.dumps(data)[:500]}")
        return False, ""

    print(f"Total trips found: {len(trips)}")

    for trip in trips:
        # Operator name field — try multiple keys
        operator = (
            trip.get("company_name")
            or trip.get("operator")
            or trip.get("bus_company_name")
            or trip.get("operatorName")
            or ""
        )

        seats_available = (
            trip.get("seat_counts", {}).get("available")
            or trip.get("available_seats")
            or trip.get("availableSeats")
            or trip.get("seats_available")
            or 0
        )

        print(f"  {operator}: {seats_available} seats")

        if TARGET_OPERATOR.lower() in operator.lower():
            print(f"Found target: {operator} — {seats_available} seats available")
            if int(seats_available) > 0:
                departure = trip.get("departure_time") or trip.get("departureTime") or ""
                return True, f"{operator} | {seats_available} seats | Departure: {departure}"

    return False, ""

def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram secrets missing — skipping notification.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, json=payload, timeout=15)
    if resp.status_code == 200:
        print("Telegram notification sent!")
    else:
        print(f"Telegram error: {resp.text}")

def main():
    print(f"Checking seats: {FROM_CITY} → {TO_CITY} on {DATE}")
    print(f"Target operator: {TARGET_OPERATOR}")
    print("-" * 40)

    token = get_token()
    found, info = check_seats(token)

    if found:
        message = (
            f"🚌 *SEAT AVAILABLE!*\n\n"
            f"*Route:* {FROM_CITY} → {TO_CITY}\n"
            f"*Date:* {DATE}\n"
            f"*{info}*\n\n"
            f"👉 Book now: https://www.shohoz.com/bus-tickets/booking/bus/search"
            f"?fromcity={FROM_CITY}&tocity={TO_CITY}&doj={DATE}"
        )
        print(message)
        send_telegram(message)
    else:
        print(f"No seats available for {TARGET_OPERATOR} yet.")

if __name__ == "__main__":
    main()
