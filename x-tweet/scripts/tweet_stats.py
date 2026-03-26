#!/usr/bin/env python3
"""Pull tweet engagement metrics via twikit.

Usage:
    python tweet_stats.py                  # Last 10 tweets
    python tweet_stats.py --count 20       # Last 20 tweets
    python tweet_stats.py --id 1234567890  # Specific tweet
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path.home() / "telegram-claude-bot" / ".env"
load_dotenv(ENV_PATH)

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


async def get_client():
    """Create authenticated twikit client."""
    from twikit import Client

    client = Client("en-US")

    cookies_path = Path.home() / "telegram-claude-bot" / "x_cookies.json"
    if cookies_path.exists():
        client.load_cookies(str(cookies_path))
    else:
        await client.login(
            auth_info_1=os.getenv("TWITTER_EMAIL"),
            auth_info_2=os.getenv("TWITTER_USERNAME"),
            password=os.getenv("TWITTER_PASSWORD"),
        )
        client.save_cookies(str(cookies_path))

    return client


async def get_user_tweets(count: int = 10):
    """Fetch recent tweets with metrics."""
    client = await get_client()

    user = await client.get_user_by_screen_name("nardovibecoding")
    tweets = await user.get_tweets("Tweets", count=count)

    results = []
    for tweet in tweets:
        data = {
            "id": tweet.id,
            "text": tweet.text[:100],
            "created_at": str(tweet.created_at),
            "likes": tweet.favorite_count,
            "retweets": tweet.retweet_count,
            "replies": tweet.reply_count,
            "bookmarks": getattr(tweet, "bookmark_count", 0),
            "views": getattr(tweet, "view_count", 0),
        }

        # Weighted engagement score
        data["score"] = (
            data["replies"] * 13.5
            + data["retweets"] * 20
            + data["bookmarks"] * 10
            + data["likes"] * 1
        )

        results.append(data)

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


async def get_tweet_stats(tweet_id: str):
    """Get stats for a specific tweet."""
    client = await get_client()
    tweet = await client.get_tweet_by_id(tweet_id)

    return {
        "id": tweet.id,
        "text": tweet.text,
        "likes": tweet.favorite_count,
        "retweets": tweet.retweet_count,
        "replies": tweet.reply_count,
        "bookmarks": getattr(tweet, "bookmark_count", 0),
        "views": getattr(tweet, "view_count", 0),
    }


async def main():
    parser = argparse.ArgumentParser(description="Tweet engagement stats")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--id", help="Specific tweet ID")
    args = parser.parse_args()

    if args.id:
        result = await get_tweet_stats(args.id)
        print(json.dumps(result, indent=2))
    else:
        results = await get_user_tweets(args.count)
        print(json.dumps(results, indent=2))

        # Save to performance file
        perf_path = DATA_DIR / "performance.json"
        existing = []
        if perf_path.exists():
            existing = json.loads(perf_path.read_text())

        # Merge by ID
        existing_ids = {t["id"] for t in existing}
        for r in results:
            if r["id"] not in existing_ids:
                existing.append(r)

        perf_path.write_text(json.dumps(existing, indent=2))
        print(f"\nSaved to {perf_path}")


if __name__ == "__main__":
    asyncio.run(main())
