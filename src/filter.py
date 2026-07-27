"""
Filter pipeline — sequentially removes posts that don't meet criteria.

Each filter function takes a list of posts, returns the survivors, and
logs how many were removed so you can tune thresholds easily.
"""

from collections import defaultdict
import logging
from datetime import datetime, timezone

import config
from src.reddit_client import Post

logger = logging.getLogger(__name__)


def _filter_by_age(posts: list[Post], stats: dict) -> list[Post]:
    """Keep only posts whose age falls within [MIN_AGE_HOURS, MAX_AGE_HOURS]."""
    now = datetime.now(tz=timezone.utc)
    survivors: list[Post] = []

    for post in posts:
        age_hours = (now - post["created_utc"]).total_seconds() / 3600
        if config.MIN_AGE_HOURS <= age_hours <= config.MAX_AGE_HOURS:
            survivors.append(post)

    removed = len(posts) - len(survivors)
    stats["dropped_age"] += removed
    logger.info("Age filter: kept %d, removed %d.", len(survivors), removed)
    return survivors


def _filter_by_keywords(posts: list[Post], stats: dict) -> list[Post]:
    """Drop posts whose title contains any blocked keyword (case-insensitive)."""
    if not config.BLOCKED_KEYWORDS:
        return posts

    blocked = [kw.lower() for kw in config.BLOCKED_KEYWORDS]
    survivors: list[Post] = []

    for post in posts:
        title_lower = post["title"].lower()
        matched = next((kw for kw in blocked if kw in title_lower), None)
        if matched:
            stats["dropped_keywords"][matched] += 1
        else:
            survivors.append(post)

    removed = len(posts) - len(survivors)
    logger.info(
        "Keyword filter: kept %d, removed %d.", len(survivors), removed
    )
    return survivors


def _filter_duplicates(posts: list[Post], stats: dict) -> list[Post]:
    """Remove cross-posts (posts with the exact same title or external url)."""
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    survivors: list[Post] = []

    for post in posts:
        title_key = post["title"].strip().lower()
        url_key = post.get("external_url", "").strip().lower()
        
        is_duplicate = False
        if title_key in seen_titles:
            is_duplicate = True
        elif url_key and url_key in seen_urls:
            is_duplicate = True
            
        if not is_duplicate:
            seen_titles.add(title_key)
            if url_key:
                seen_urls.add(url_key)
            survivors.append(post)

    removed = len(posts) - len(survivors)
    stats["dropped_duplicates"] += removed
    logger.info("Duplicate filter: kept %d, removed %d.", len(survivors), removed)
    return survivors


def apply_filters(posts: list[Post]) -> tuple[list[Post], dict]:
    """
    Run every filter in sequence.
    Returns the surviving posts and a stats dictionary.
    """
    stats = {
        "dropped_age": 0,
        "dropped_duplicates": 0,
        "dropped_keywords": defaultdict(int)
    }
    logger.info("Starting filters on %d posts …", len(posts))
    posts = _filter_by_age(posts, stats)
    posts = _filter_by_keywords(posts, stats)
    posts = _filter_duplicates(posts, stats)
    logger.info("After all filters: %d posts remain.", len(posts))
    
    # Convert defaultdict to normal dict for JSON serialization
    stats["dropped_keywords"] = dict(stats["dropped_keywords"])
    return posts, stats
