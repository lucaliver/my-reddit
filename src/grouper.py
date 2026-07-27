"""
Group posts by subreddit (or custom subreddit group) and cap them.

Posts within each group are ordered by recency (newest first) and
capped at MAX_POSTS_PER_GROUP / MAX_POSTS_PER_SUBREDDIT.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

import config
from src.reddit_client import Post

logger = logging.getLogger(__name__)


@dataclass
class PostGroup:
    """A named cluster of posts from one or more subreddits."""

    name: str
    subreddits: set[str] = field(default_factory=set)
    posts: list[Post] = field(default_factory=list)


    @property
    def subreddits_label(self) -> str:
        """Human-readable list of subreddits, e.g. 'r/python, r/webdev'."""
        return ", ".join(f"r/{s}" for s in sorted(self.subreddits))


def _build_subreddit_to_group() -> dict[str, str]:
    """
    Invert SUBREDDIT_GROUPS into a lookup: subreddit_name → group_name.

    Subreddits are normalised to lowercase.
    """
    mapping: dict[str, str] = {}
    for group_name, subs in config.SUBREDDIT_GROUPS.items():
        for sub in subs:
            mapping[sub.lower()] = group_name
    return mapping


def group_posts(posts: list[Post]) -> list[PostGroup]:
    """
    Assign each post to a group, sort, and cap per-group count.

    Returns the groups ordered by post count (descending).
    """
    sub_to_group = _build_subreddit_to_group()
    buckets: dict[str, PostGroup] = defaultdict(lambda: PostGroup(name=""))

    for post in posts:
        sub = post["subreddit"]
        group_name = sub_to_group.get(sub, post["subreddit_display"])

        group = buckets[group_name]
        group.name = group_name
        group.subreddits.add(sub)
        group.posts.append(post)

    # Sort posts inside each group by recency (newest first) and cap
    for group in buckets.values():
        group.posts.sort(key=lambda p: p["created_utc"], reverse=True)
        
        filtered_posts = []
        sub_counts = defaultdict(int)
        for p in group.posts:
            if sub_counts[p["subreddit"]] < config.MAX_POSTS_PER_SUBREDDIT:
                filtered_posts.append(p)
                sub_counts[p["subreddit"]] += 1
            if len(filtered_posts) == config.MAX_POSTS_PER_GROUP:
                break
        group.posts = filtered_posts

    # Sort groups by post count (most posts first)
    result = sorted(buckets.values(), key=lambda g: len(g.posts), reverse=True)

    logger.info(
        "Grouped into %d groups (cap %d posts/group).",
        len(result),
        config.MAX_POSTS_PER_GROUP,
    )
    return result
