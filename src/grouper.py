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
        """Human-readable list of subreddits, ordered by post count descending."""
        counts = {s: 0 for s in self.subreddits}
        for p in self.posts:
            if p["subreddit"] in counts:
                counts[p["subreddit"]] += 1
                
        # Sort by post count (descending), then alphabetically
        ordered = sorted(self.subreddits, key=lambda s: (-counts.get(s, 0), s.lower()))
        return ", ".join(f"r/{s}" for s in ordered)


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

    # Sort groups matching the order defined in config.SUBREDDIT_GROUPS
    config_order = list(config.SUBREDDIT_GROUPS.keys())
    
    def group_sort_key(g: PostGroup) -> int:
        try:
            return config_order.index(g.name)
        except ValueError:
            return 999  # Put unknown standalone groups at the end
            
    result = sorted(buckets.values(), key=group_sort_key)

    logger.info(
        "Grouped into %d groups (cap %d posts/group).",
        len(result),
        config.MAX_POSTS_PER_GROUP,
    )
    return result
