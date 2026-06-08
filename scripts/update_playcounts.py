#!/usr/bin/env python3
"""
Fetch the latest play counts for each audiobook from Ximalaya and update data.json
in place. Designed to run inside GitHub Actions (cloud), so it does not depend on
any local machine being online.
"""
import json
import sys
from datetime import datetime, timezone, timedelta

import requests

DATA_PATH = "data.json"
CHINA_TZ = timezone(timedelta(hours=8))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.ximalaya.com/",
    "Accept": "application/json, text/plain, */*",
}


def fetch_play_count(album_id: int) -> int:
    url = f"https://www.ximalaya.com/revision/album/v1/simple?albumId={album_id}"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    return int(payload["data"]["albumPageMainInfo"]["playCount"])


def main() -> int:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now(CHINA_TZ).strftime("%Y-%m-%d")
    failures = []

    for work in data.get("works", []):
        album_id = work.get("id")
        try:
            play_count = fetch_play_count(album_id)
            work["playCount"] = play_count
            work["updated"] = today
            print(f"OK  {album_id:>10}  {work.get('title', ''):<20}  playCount={play_count}")
        except Exception as exc:  # noqa: BLE001
            failures.append((album_id, str(exc)))
            print(f"FAIL {album_id:>10}  {work.get('title', ''):<20}  error={exc}", file=sys.stderr)

    data["updatedAt"] = today

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")

    total = len(data.get("works", []))
    ok = total - len(failures)
    print(f"\nUpdated {ok}/{total} works for {today}.")

    if failures:
        print(f"::warning::{len(failures)} album(s) failed to update: {failures}")
        # Don't hard-fail the whole job for partial failures — keep whatever succeeded.
        # If EVERYTHING failed, treat it as an error so the workflow surfaces it.
        if ok == 0:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
