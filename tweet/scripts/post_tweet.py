#!/usr/bin/env python3
# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Post tweets via X API v2 (OAuth 1.0a User Context).

Usage:
    python post_tweet.py "Tweet text here"
    python post_tweet.py "Tweet text" --reply-to 1234567890
    python post_tweet.py "Tweet text" --media /path/to/image.png
"""

import argparse
import json
import os
from pathlib import Path
from typing import Optional

import tweepy
from dotenv import load_dotenv

# Load env from telegram-claude-bot/.env
ENV_PATH = Path.home() / "telegram-claude-bot" / ".env"
load_dotenv(ENV_PATH)


def get_client() -> tweepy.Client:
    """Create authenticated X API v2 client."""
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def get_api_v1() -> tweepy.API:
    """Create v1.1 API for media uploads (v2 doesn't support media upload)."""
    auth = tweepy.OAuth1UserHandler(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    return tweepy.API(auth)


def upload_media(image_path: str) -> str:
    """Upload media and return media_id."""
    api = get_api_v1()
    media = api.media_upload(image_path)
    return media.media_id_string


def post_tweet(
    text: str,
    reply_to: Optional[str] = None,
    media_path: Optional[str] = None,
) -> dict:
    """Post a tweet. Returns tweet data."""
    if len(text) > 280:
        raise ValueError(f"Tweet exceeds 280 chars ({len(text)}). No threads — trim first.")

    client = get_client()

    kwargs: dict = {}

    if reply_to:
        kwargs["in_reply_to_tweet_id"] = reply_to

    if media_path:
        media_id = upload_media(media_path)
        kwargs["media_ids"] = [int(media_id)]

    response = client.create_tweet(text=text, **kwargs)

    tweet_id = response.data["id"]  # type: ignore[index]
    url = f"https://x.com/nardovibecoding/status/{tweet_id}"

    return {
        "id": tweet_id,
        "text": text,
        "url": url,
    }


def send_tg_alert(tweet_data: dict) -> None:
    """Send notification to TG topic thread."""
    import requests

    bot_token = os.getenv("ADMIN_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN_ADMIN")
    if not bot_token:
        return

    chat_id = -1003827304557
    thread_id = 313

    message = f"Tweet posted:\n{tweet_data['url']}\n\n{tweet_data['text'][:200]}"

    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "message_thread_id": thread_id,
            "text": message,
            "disable_web_page_preview": False,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Post tweet via X API")
    parser.add_argument("text", help="Tweet text")
    parser.add_argument("--reply-to", help="Tweet ID to reply to")
    parser.add_argument("--media", help="Path to image to attach")
    parser.add_argument("--no-alert", action="store_true", help="Skip TG notification")
    args = parser.parse_args()

    result = post_tweet(args.text, args.reply_to, args.media)
    print(json.dumps(result, indent=2))

    if not args.no_alert:
        send_tg_alert(result)
        print("TG alert sent.")


if __name__ == "__main__":
    main()
