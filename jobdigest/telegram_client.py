import time
import requests


def send_telegram_digest(chunks: list, bot_token: str, chat_id: str) -> None:
    if not bot_token or not chat_id:
        print("ERROR: Telegram bot token or chat id not set; skipping send.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for i, chunk in enumerate(chunks, start=1):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        for attempt in range(3):
            try:
                res = requests.post(url, json=payload, timeout=20)
                if res.status_code == 200:
                    print(f"Telegram chunk {i}/{len(chunks)} sent.")
                    break
                print(f"Telegram send failed (chunk {i}, attempt "
                      f"{attempt + 1}/3): {res.status_code} {res.text}")
            except Exception as e:
                print(f"Telegram send error (chunk {i}, attempt "
                      f"{attempt + 1}/3): {e}")
            time.sleep(2 ** attempt)
        else:
            print(f"Giving up on chunk {i}/{len(chunks)} after 3 attempts.")

