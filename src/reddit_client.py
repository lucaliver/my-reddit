"""
Fetch posts from Reddit subreddits via public RSS feeds.

No API key or authentication required — uses the public ``.rss`` endpoint.
All subreddits are fetched in a single multi-subreddit request
(``r/sub1+sub2+sub3/top.rss``) to avoid rate limiting.

Returns a list of normalised post dicts consumed by the filter/grouper.

Note: Reddit's RSS/Atom feeds do **not** expose post scores. We rely on 
Reddit's own ``top`` sorting to surface high-quality posts and use age 
filtering to keep only mature posts (24-48h by default).
"""

from __future__ import annotations

import html as html_module
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests
from bs4 import BeautifulSoup
from tenacity import retry, wait_exponential, retry_if_exception_type, stop_after_attempt

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
_RETRY_BASE_DELAY = 45.0  # seconds, long cooldown if we hit a limit

# Delay between batch requests when subreddits are split into chunks
_BATCH_DELAY_SECONDS = 20.0


@retry(
    stop=stop_after_attempt(_MAX_RETRIES),
    wait=wait_exponential(multiplier=_RETRY_BASE_DELAY, max=300),
    retry=retry_if_exception_type(requests.HTTPError),
    reraise=True
)
def _do_request(url: str, params: dict, headers: dict) -> str:
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code == 429:
        logger.info("Rate-limited (429), tenacity will retry...")
    resp.raise_for_status()
    return resp.text


def _fetch_rss(subreddits_str: str, sort: str, limit: int) -> str | None:
    """
    Download the RSS XML for a multi-subreddit feed.

    Retries with exponential backoff on HTTP errors.
    """
    url = _RSS_URL.format(subreddits=subreddits_str, sort=sort)
    params = {"limit": str(limit), "t": "week"}
    headers = {"User-Agent": _USER_AGENT}

    try:
        return _do_request(url, params, headers)
    except requests.RequestException as exc:
        logger.warning("Failed to fetch RSS: %s", exc)
        return None


def _parse_rss(xml_text: str) -> list[Post]:
    """
    Parse Reddit's Atom feed into normalised Post dicts.
    Extracts thumbnail and excerpt from HTML payload where possible.
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

        # Try to extract thumbnails and external URL from content HTML
        thumbnail = None
        external_url = permalink
        
        if content_el is not None and content_el.text:
            raw_html = html_module.unescape(content_el.text)
            soup = BeautifulSoup(raw_html, "html.parser")
            
            img_tag = soup.find("img")
            if img_tag and img_tag.get("src"):
                thumbnail = img_tag["src"]
                
            link_tag = soup.find("a", string="[link]")
            if link_tag and link_tag.get("href"):
                external_url = link_tag["href"]

        # Determine media type
        media_type = "text"
        url_for_check = external_url.lower()
        if "v.redd.it" in url_for_check or "youtu.be" in url_for_check or "youtube.com" in url_for_check or url_for_check.endswith((".mp4", ".gif", ".gifv", ".webm")):
            media_type = "video"
        elif "/gallery/" in url_for_check or "reddit.com/gallery/" in permalink.lower():
            media_type = "gallery"
        elif url_for_check.endswith((".jpg", ".jpeg", ".png", ".webp")):
            media_type = "image"
        elif thumbnail:
            media_type = "image"

        # Extract post ID from the <id> element (format: t3_xxxxx)
        id_el = entry.find(f"{{{_ATOM_NS}}}id")
        post_id = id_el.text if id_el is not None and id_el.text else permalink

        posts.append(
            {
                "id": post_id,
                "title": title,
                "subreddit": subreddit.lower(),
                "subreddit_display": subreddit_display,
                "url": external_url,
                "external_url": external_url,
                "permalink": permalink,
                "created_utc": created_utc,
                "is_self": "/comments/" in permalink,
                "over_18": False,
                "thumbnail": thumbnail,
                "media_type": media_type,
            }
        )

    return posts



def _chunk_list(items: list[str], chunk_size: int) -> list[list[str]]:
    """Split a list into chunks of at most chunk_size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def fetch_feed() -> list[Post]:
    """
    Fetch posts from all configured subreddits via RSS.

    Fetches each group separately so that high-traffic subreddits in one group
    don't saturate the 100-post limit and drown out smaller subreddits.
    """
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
        
        # limit proportional to chunk size, capped at FETCH_LIMIT
        chunk_limit = min(config.FETCH_LIMIT, len(clean_chunk) * 15)
        
        xml_text = _fetch_rss(subs_str, config.FEED_SORT, chunk_limit)
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
