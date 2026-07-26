#!/usr/bin/env python3
"""
my-reddit — personalised Reddit digest delivered to Telegram.

Entry point: fetches the home feed, filters it, groups posts by subreddit,
and sends the result as a formatted Telegram message.
"""

import logging
import sys
import time

from src import reddit_client, filter as post_filter, grouper, telegram_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-5s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("my-reddit")


def main() -> None:
    start_time = time.time()
    logger.info("Pipeline started.")

    # 1. Fetch
    posts = reddit_client.fetch_feed()
    if not posts:
        logger.warning("No posts fetched — aborting.")
        return

    # 2. Filter
    posts = post_filter.apply_filters(posts)
    if not posts:
        logger.warning("All posts filtered out — nothing to send.")
        return

    # 3. Group
    groups = grouper.group_posts(posts)

    # 4. Format & send
    telegram_sender.send_digest(groups)

    total_posts = sum(len(g.posts) for g in groups)
    elapsed = time.time() - start_time
    logger.info(
        "Done — sent %d posts across %d groups in %.1f seconds.", 
        total_posts, len(groups), elapsed
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal error in my-reddit pipeline.")
        sys.exit(1)
