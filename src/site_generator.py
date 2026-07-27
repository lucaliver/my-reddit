"""
Generate a JSON digest file for the static landing page.

Converts the grouped posts into a structured ``digest.json`` that the
front-end (``site/index.html``) loads and renders client-side.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
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
        "created_utc": created_iso,
        "thumbnail": post.get("thumbnail"),
        "media_type": post.get("media_type", "text"),
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


def generate_digest_json(groups: list[PostGroup], stats: dict) -> None:
    """
    Write ``digest.json`` into the configured output directory,
    and archive a copy into ``site/archive/``.
    """
    output_dir = config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    total_posts = sum(len(g.posts) for g in groups)
    now = datetime.now(tz=timezone.utc)

    digest = {
        "generated_at": now.isoformat(),
        "total_posts": total_posts,
        "total_groups": len(groups),
        "stats": stats,
        "groups": [_serialize_group(g) for g in groups],
    }

    output_path = os.path.join(output_dir, "digest.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    # Archiving logic
    archive_dir = os.path.join(output_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    
    date_str = now.strftime("%Y-%m-%d")
    archive_filename = f"digest_{date_str}.json"
    archive_path = os.path.join(archive_dir, archive_filename)
    
    shutil.copy2(output_path, archive_path)
    
    index_path = os.path.join(archive_dir, "index.json")
    archive_index = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                archive_index = json.load(f)
        except Exception:
            pass
            
    # Remove existing entry for same date if present
    archive_index = [entry for entry in archive_index if entry["date"] != date_str]
    
    # Insert at the beginning
    archive_index.insert(0, {
        "date": date_str,
        "filename": archive_filename,
        "generated_at": now.isoformat()
    })
    
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(archive_index, f, ensure_ascii=False, indent=2)

    logger.info(
        "Wrote digest.json — %d posts across %d groups → %s",
        total_posts, len(groups), output_path,
    )
