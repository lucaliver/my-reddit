"""
Generate a JSON digest file for the static landing page.

Converts the grouped posts into a structured ``digest.json`` that the
front-end (``site/index.html``) loads and renders client-side.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import config
from src.grouper import PostGroup

logger = logging.getLogger(__name__)


def _serialize_post(post: dict) -> dict:
    """Convert a post dict to a JSON-safe representation."""
    created = post.get("created_utc")
    if isinstance(created, datetime):
        created_iso = created.isoformat()
    else:
        created_iso = str(created) if created else None

    return {
        "title": post["title"],
        "url": post["permalink"],
        "subreddit": post["subreddit_display"],
        "num_comments": post.get("num_comments", 0),
        "created_utc": created_iso,
    }


def _serialize_group(group: PostGroup) -> dict:
    """Convert a PostGroup to a JSON-safe dict."""
    return {
        "name": group.name,
        "subreddits": sorted(group.subreddits),
        "subreddits_label": group.subreddits_label,
        "post_count": len(group.posts),
        "posts": [_serialize_post(p) for p in group.posts],
    }


def generate_digest_json(groups: list[PostGroup]) -> None:
    """
    Write ``digest.json`` into the configured output directory.

    The JSON structure:
    {
        "generated_at": "2026-07-26T16:00:00+00:00",
        "total_posts": 123,
        "total_groups": 18,
        "groups": [ ... ]
    }
    """
    output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    total_posts = sum(len(g.posts) for g in groups)
    now = datetime.now(tz=timezone.utc)

    digest = {
        "generated_at": now.isoformat(),
        "total_posts": total_posts,
        "total_groups": len(groups),
        "groups": [_serialize_group(g) for g in groups],
    }

    output_path = os.path.join(output_dir, "digest.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    logger.info(
        "Wrote digest.json — %d posts across %d groups → %s",
        total_posts, len(groups), output_path,
    )
