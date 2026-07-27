"""
Filter pipeline — sequentially removes posts that don't meet criteria.

Each filter function takes a list of posts, returns the survivors, and
logs how many were removed so you can tune thresholds easily.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import config
from src.reddit_client import Post

logger = logging.getLogger(__name__)


def _filter_by_age(posts: list[Post]) -> list[Post]:
    """Keep only posts whose age falls within [MIN_AGE_HOURS, MAX_AGE_HOURS]."""
    now = datetime.now(tz=timezone.utc)
    survivors: list[Post] = []

    for post in posts:
        age_hours = (now - post["created_utc"]).total_seconds() / 3600
        if config.MIN_AGE_HOURS <= age_hours <= config.MAX_AGE_HOURS:
            survivors.append(post)

    removed = len(posts) - len(survivors)
    logger.info("Age filter: kept %d, removed %d.", len(survivors), removed)
    return survivors


def _filter_by_keywords(posts: list[Post]) -> list[Post]:
    """Drop posts whose title contains any blocked keyword (case-insensitive)."""
    if not config.BLOCKED_KEYWORDS:
        return posts

    blocked = [kw.lower() for kw in config.BLOCKED_KEYWORDS]
    survivors: list[Post] = []

    for post in posts:
        title_lower = post["title"].lower()
        if not any(kw in title_lower for kw in blocked):
            survivors.append(post)

    removed = len(posts) - len(survivors)
    logger.info(
        "Keyword filter: kept %d, removed %d.", len(survivors), removed
    )
    return survivors


def apply_filters(posts: list[Post]) -> list[Post]:
    """
    Run every filter in sequence.

    Order matters: age first (cheapest), then keywords.
    """
    logger.info("Starting filters on %d posts …", len(posts))
    posts = _filter_by_age(posts)
    posts = _filter_by_keywords(posts)
    logger.info("After all filters: %d posts remain.", len(posts))
    return posts
