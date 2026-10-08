import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests


NOTE_BASE = "https://note.com"

INPUT = Path(
    os.environ.get(
        "PREDICTION_JSON",
        "data/prediction/v59_today.json",
    )
)

EYECATCH = Path("output/eyecatch.png")
PUBLISHED_DIR = Path("data/published")

DRY_RUN = (
    os.environ.get("DRY_RUN", "true")
    .strip()
    .lower()
    == "true"
)


def fail(message):
    print("")
    print("==============================")
    print("PUBLISH FAILED")
    print("==============================")
    print(message)
    sys.exit(1)


def safe_filename(value):
    value = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        value,
    )
    return value.strip("_")


def load_article():
    if not INPUT.exists():
        fail(f"Input file does not exist: {INPUT}")

    try:
        data = json.loads(
            INPUT.read_text(encoding="utf-8")
        )
    except Exception as exc:
        fail(f"Invalid JSON: {exc}")

    required = [
        "prediction_id",
        "title",
        "article",
    ]

    missing = [
        key
        for key in required
        if not data.get(key)
    ]

    if missing:
        fail(
            "Missing required fields: "
            + ", ".join(missing)
        )

    return data


def build_session():
    cookie = os.environ.get(
        "NOTE_COOKIE",
        "",
    ).strip()

    if not cookie:
        fail("NOTE_COOKIE is not configured.")

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Origin": NOTE_BASE,
        "Referer": NOTE_BASE + "/",
        "Cookie": cookie,
    })

    return session


def check_auth(session):
    response = session.get(
        NOTE_BASE + "/api/v3/notice_counts",
        timeout=30,
    )

    print("AUTH STATUS:", response.status_code)

    if response.status_code != 200:
        fail(
            "note authentication failed. "
            f"HTTP {response.status_code}"
        )


def create_draft(session, title):
    response = session.post(
        NOTE_BASE + "/api/v1/text_notes",
        json={
            "name": title,
        },
        timeout=30,
    )

    print(
        "CREATE DRAFT STATUS:",
        response.status_code,
    )

    if response.status_code not in (
        200,
        201,
    ):
        fail(
            "Draft creation failed: "
            + response.text[:500]
        )

    payload = response.json()

    note = payload.get("data", payload)

    note_id = (
        note.get("id")
        or note.get("note_id")
    )

    key = (
        note.get("key")
        or note.get("note_key")
    )

    if not note_id:
        fail(
            "note id was not returned: "
            + response.text[:500]
        )

    return note_id, key


def save_body(
    session,
    note_id,
    title,
    article,
):
    url = (
        NOTE_BASE
        + "/api/v1/text_notes/draft_save"
        + f"?id={note_id}"
        + "&is_temp_saved=true"
    )

    payload = {
        "name": title,
        "body": article,
    }

    response = session.post(
        url,
        json=payload,
        timeout=30,
    )

    print(
        "SAVE BODY STATUS:",
        response.status_code,
    )

    if response.status_code not in (
        200,
        201,
    ):
        fail(
            "Body save failed: "
            + response.text[:500]
        )


def upload_eyecatch(session):
    if not EYECATCH.exists():
        fail(
            f"Eyecatch does not exist: {EYECATCH}"
        )

    with EYECATCH.open("rb") as fp:
        response = session.post(
            NOTE_BASE
            + "/api/v1/image_upload/note_eyecatch",
            files={
                "file": (
                    EYECATCH.name,
                    fp,
                    "image/png",
                )
            },
            timeout=60,
        )

    print(
        "EYECATCH UPLOAD STATUS:",
        response.status_code,
    )

    if response.status_code not in (
        200,
        201,
    ):
        fail(
            "Eyecatch upload failed: "
            + response.text[:500]
        )

    payload = response.json()

    data = payload.get(
        "data",
        payload,
    )

    return (
        data.get("url")
        or data.get("image_url")
        or data.get("key")
    )


def publish_note(
    session,
    note_id,
    title,
    article,
    hashtags,
    eyecatch,
):
    payload = {
        "name": title,
        "body": article,
        "hashtags": hashtags,
        "status": "published",
        "send_notifications_flag": False,
    }

    if eyecatch:
        payload["eyecatch"] = eyecatch

    response = session.put(
        NOTE_BASE
        + f"/api/v1/text_notes/{note_id}",
        json=payload,
        timeout=30,
    )

    print(
        "PUBLISH STATUS:",
        response.status_code,
    )

    if response.status_code not in (
        200,
        201,
    ):
        fail(
            "Publish failed: "
            + response.text[:1000]
        )

    return response.json()


def extract_note_key(payload):
    data = payload.get(
        "data",
        payload,
    )

    if not isinstance(data, dict):
        return None

    return (
        data.get("key")
        or data.get("note_key")
    )


def verify_public(session, key):
    if not key:
        print(
            "PUBLIC VERIFY: "
            "SKIPPED - key unavailable"
        )
        return

    response = session.get(
        NOTE_BASE
        + f"/api/v3/notes/{key}",
        timeout=30,
    )

    print(
        "PUBLIC VERIFY STATUS:",
        response.status_code,
    )

    if response.status_code != 200:
        fail(
            "Public verification failed. "
            f"HTTP {response.status_code}"
        )

    print("PUBLIC VERIFY: PASS")


def create_marker(
    prediction_id,
    title,
    key,
):
    PUBLISHED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    marker = (
        PUBLISHED_DIR
        / (
            safe_filename(prediction_id)
            + ".json"
        )
    )

    marker_data = {
        "prediction_id": prediction_id,
        "title": title,
        "note_key": key,
    }

    marker.write_text(
        json.dumps(
            marker_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "PUBLICATION MARKER:",
        marker,
    )


def main():
    print("==============================")
    print("v5.9 NOTE PUBLISHER")
    print("==============================")

    data = load_article()

    prediction_id = str(
        data["prediction_id"]
    )

    title = str(
        data["title"]
    ).strip()

    article = str(
        data["article"]
    ).strip()

    hashtags = data.get(
        "hashtags",
        [],
    )

    if not hashtags:
        hashtags = [
            "#日本株",
            "#日本株投資",
            "#株式投資",
            "#デイトレ",
            "#短期投資",
            "#株価予想",
            "#注目銘柄",
            "#急騰株",
            "#ストップ高",
            "#AI投資",
        ]

    # Duplicate protection
    PUBLISHED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    marker = (
        PUBLISHED_DIR
        / (
            safe_filename(prediction_id)
            + ".json"
        )
    )

    if marker.exists():
        fail(
            "This prediction has already "
            f"been published: {marker}"
        )

    print("PREDICTION ID:", prediction_id)
    print("TITLE:", title)
    print("ARTICLE LENGTH:", len(article))
    print(
        "HASHTAGS:",
        " ".join(hashtags),
    )
    print("DRY RUN:", DRY_RUN)

    if DRY_RUN:
        print("")
        print("==============================")
        print("DRY RUN COMPLETE")
        print("==============================")
        return

    session = build_session()

    check_auth(session)

    note_id, draft_key = create_draft(
        session,
        title,
    )

    print("NOTE ID:", note_id)

    save_body(
        session,
        note_id,
        title,
        article,
    )

    eyecatch = upload_eyecatch(
        session
    )

    print(
        "EYECATCH:",
        eyecatch,
    )

    result = publish_note(
        session,
        note_id,
        title,
        article,
        hashtags,
        eyecatch,
    )

    key = (
        extract_note_key(result)
        or draft_key
    )

    verify_public(
        session,
        key,
    )

    create_marker(
        prediction_id,
        title,
        key,
    )

    print("")
    print("==============================")
    print("NOTE PUBLISH: PASS")
    print("==============================")

    if key:
        print(
            "NOTE:",
            f"https://note.com/n/n{key}",
        )


if __name__ == "__main__":
    main()
