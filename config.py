"""
Central configuration for the Reddit feed pipeline.

All values have sensible defaults and can be overridden via environment
variables, making the project easy to reconfigure without code changes.
A ``.env`` file in the project root is loaded automatically for local runs.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()  # loads .env from the working directory, if present


# ---------------------------------------------------------------------------
# Output directory for the generated site
# ---------------------------------------------------------------------------
OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "site")

# ---------------------------------------------------------------------------
# Subreddits to follow (required — at least one source needed)
#
# Plain list of subreddits not assigned to any group.
# Supply as a JSON array string via env, e.g. '["funny","pics","aww"]'
# ---------------------------------------------------------------------------
_default_subs: list[str] = []
SUBREDDITS: list[str] = json.loads(
    os.environ.get("SUBREDDITS") or json.dumps(_default_subs)
)

# ---------------------------------------------------------------------------
# Subreddit grouping
#
# Map a human-friendly group name to a list of subreddit names.
# These subreddits are fetched automatically — no need to repeat them in
# SUBREDDITS above. Subreddits not in any group get a standalone group.
#
# Supply as a JSON object string via env to override.
#
# Omitted from defaults (low signal for a daily digest):
#   4CHR, announcements, beta
# ---------------------------------------------------------------------------
def _load_groups() -> dict[str, list[str]]:
    try:
        with open("groups.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

SUBREDDIT_GROUPS: dict[str, list[str]] = json.loads(
    os.environ.get("SUBREDDIT_GROUPS") or json.dumps(_load_groups())
)

# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------
# RSS sorting: "hot", "new", "top", "rising"
# "top" is recommended — it lets Reddit rank by score for us, since
# scores are not available in the RSS feed.
FEED_SORT: str = os.environ.get("FEED_SORT", "top")

# How many posts to request (applied to the combined multi-sub feed)
FETCH_LIMIT: int = int(os.environ.get("FETCH_LIMIT", "100"))

# ---------------------------------------------------------------------------
# Filtering thresholds
# ---------------------------------------------------------------------------
# Discard posts younger than this (hours)
MIN_AGE_HOURS: int = int(os.environ.get("MIN_AGE_HOURS", "12"))

# Discard posts older than this (hours) — 168 = 7 days for weekly digest
MAX_AGE_HOURS: int = int(os.environ.get("MAX_AGE_HOURS", "168"))

# ---------------------------------------------------------------------------
# Blocked keywords — posts whose title contains any of these are dropped.
# Supply as a JSON array string via env, e.g. '["crypto","nft"]'
# ---------------------------------------------------------------------------
_default_keywords: list[str] = ["trump"]
BLOCKED_KEYWORDS: list[str] = json.loads(
    os.environ.get("BLOCKED_KEYWORDS", json.dumps(_default_keywords))
)

# Maximum posts shown per group in the final digest
MAX_POSTS_PER_GROUP: int = int(os.environ.get("MAX_POSTS_PER_GROUP", "10"))

# Maximum posts shown per individual subreddit in the final digest
MAX_POSTS_PER_SUBREDDIT: int = int(os.environ.get("MAX_POSTS_PER_SUBREDDIT", "3"))
