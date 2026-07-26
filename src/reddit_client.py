"""
Fetch posts from Reddit subreddits via public RSS feeds.

No API key or authentication required — uses the public ``.rss`` endpoint.
All subreddits are fetched in a single multi-subreddit request
(``r/sub1+sub2+sub3/top.rss``) to avoid rate limiting.

Returns a list of normalised post dicts consumed by the filter/grouper.

Note: Reddit's RSS/Atom feeds do **not** expose post scores or comment
counts. We rely on Reddit's own ``top`` sorting to surface high-quality
posts and use age filtering to keep only mature posts (24-48h by default).
"""

from __future__ import annotations

import html as html_module
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)

Post = dict[str, Any]

_RSS_URL = "https://www.reddit.com/r/{subreddits}/{sort}.rss"
_USER_AGENT = "my-reddit-digest/1.0 (personal feed aggregator)"

# Atom namespace used by Reddit's RSS feed
_ATOM_NS = "http://www.w3.org/2005/Atom"

# Maximum subreddits per multi-sub request (Reddit has a URL length limit)
_MAX_SUBS_PER_REQUEST = 50

# Retry settings for 429 (Too Many Requests)
_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 30.0  # seconds, doubles on each retry

# Delay between batch requests when subreddits are split into chunks
_BATCH_DELAY_SECONDS = 45.0


def _fetch_rss(subreddits_str: str, sort: str, limit: int) -> str | None:
    """
    Download the RSS XML for a multi-subreddit feed.

    Retries with exponential backoff on 429 responses.
    """
    url = _RSS_URL.format(subreddits=subreddits_str, sort=sort)
    params = {"limit": str(limit), "t": "week"}
    headers = {"User-Agent": _USER_AGENT}

    import time

    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError:
            if resp.status_code == 429 and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.info(
                    "Rate-limited (429), retrying in %.0fs …", wait
                )
                time.sleep(wait)
                continue
            logger.warning(
                "Failed to fetch RSS (HTTP %d): %s",
                resp.status_code, subreddits_str[:80],
            )
            return None
        except requests.RequestException as exc:
            logger.warning("Failed to fetch RSS: %s", exc)
            return None

    return None


def _parse_rss(xml_text: str) -> list[Post]:
    """
    Parse Reddit's Atom feed into normalised Post dicts.

    The ``<category>`` element tells us which subreddit each entry belongs to.
    Score and comment counts are not available in RSS — we set them to 0.
    """
    posts: list[Post] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("XML parse error: %s", exc)
        return posts

    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        title_el = entry.find(f"{{{_ATOM_NS}}}title")
        link_el = entry.find(f"{{{_ATOM_NS}}}link")
        updated_el = entry.find(f"{{{_ATOM_NS}}}updated")
        category_el = entry.find(f"{{{_ATOM_NS}}}category")
        content_el = entry.find(f"{{{_ATOM_NS}}}content")

        if title_el is None or link_el is None:
            continue

        title = title_el.text or ""
        permalink = link_el.attrib.get("href", "")

        # Subreddit from <category term="python" label="r/Python"/>
        if category_el is not None:
            subreddit = category_el.attrib.get("term", "unknown")
            subreddit_display = category_el.attrib.get("label", f"r/{subreddit}")
            # Strip "r/" prefix from display label if present
            if subreddit_display.startswith("r/"):
                subreddit_display = subreddit_display[2:]
        else:
            subreddit = "unknown"
            subreddit_display = "unknown"

        # Parse the timestamp
        created_utc = datetime.now(tz=timezone.utc)
        if updated_el is not None and updated_el.text:
            try:
                created_utc = datetime.fromisoformat(updated_el.text)
            except ValueError:
                try:
                    created_utc = parsedate_to_datetime(updated_el.text)
                except (ValueError, TypeError):
                    pass

        # Try to extract comment count from content HTML
        num_comments = 0
        if content_el is not None and content_el.text:
            raw_html = html_module.unescape(content_el.text)
            m = re.search(r"\[(\d+)\s+comments?\]", raw_html)
            if m:
                num_comments = int(m.group(1))

        # Extract post ID from the <id> element (format: t3_xxxxx)
        id_el = entry.find(f"{{{_ATOM_NS}}}id")
        post_id = id_el.text if id_el is not None and id_el.text else permalink

        posts.append(
            {
                "id": post_id,
                "title": title,
                "score": 0,  # not available via RSS
                "num_comments": num_comments,
                "subreddit": subreddit.lower(),
                "subreddit_display": subreddit_display,
                "url": permalink,
                "permalink": permalink,
                "created_utc": created_utc,
                "is_self": "/comments/" in permalink,
                "over_18": False,
            }
        )

    return posts


def _collect_subreddits() -> list[str]:
    """
    Build the full de-duplicated list of subreddits from config.

    Merges SUBREDDITS and all subs mentioned in SUBREDDIT_GROUPS.
    """
    subs: set[str] = set()

    for sub in config.SUBREDDITS:
        subs.add(sub.lower())

    for group_subs in config.SUBREDDIT_GROUPS.values():
        for sub in group_subs:
            subs.add(sub.lower())

    return sorted(subs)


def _chunk_list(items: list[str], chunk_size: int) -> list[list[str]]:
    """Split a list into chunks of at most chunk_size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def fetch_feed() -> list[Post]:
    """
    Fetch posts from all configured subreddits via RSS.

    Fetches each group separately so that high-traffic subreddits in one group
    don't saturate the 100-post limit and drown out smaller subreddits.
    """
    import time

    logger.info("Starting RSS fetch (sort=%s, limit=%d) …", config.FEED_SORT, config.FETCH_LIMIT)

    seen_ids: set[str] = set()
    all_posts: list[Post] = []
    
    # Collect all chunks to fetch (group chunks + standalone chunks)
    all_chunks: list[list[str]] = []
    
    for group_name, group_subs in config.SUBREDDIT_GROUPS.items():
        if group_subs:
            all_chunks.extend(_chunk_list(group_subs, _MAX_SUBS_PER_REQUEST))
            
    if config.SUBREDDITS:
        all_chunks.extend(_chunk_list(config.SUBREDDITS, _MAX_SUBS_PER_REQUEST))

    if not all_chunks:
        logger.error(
            "No subreddits configured. Set SUBREDDITS or SUBREDDIT_GROUPS "
            "in your .env file."
        )
        return []

    for i, chunk in enumerate(all_chunks):
        if i > 0:
            time.sleep(_BATCH_DELAY_SECONDS)

        # lowercase all subs
        clean_chunk = [sub.lower() for sub in chunk]
        subs_str = "+".join(clean_chunk)
        
        xml_text = _fetch_rss(subs_str, config.FEED_SORT, config.FETCH_LIMIT)
        if xml_text is None:
            continue

        posts = _parse_rss(xml_text)
        for post in posts:
            if post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                all_posts.append(post)

        logger.info(
            "  Batch %d/%d [OK] (%s...): %d posts retrieved",
            i + 1, len(all_chunks), subs_str[:80], len(posts),
        )

    logger.info("Fetched %d unique posts total.", len(all_posts))
    return all_posts
