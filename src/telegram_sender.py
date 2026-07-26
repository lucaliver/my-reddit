"""
Format the grouped posts into a Telegram-friendly message and send it.

Uses the Telegram Bot API directly via ``requests`` — no extra SDK needed.
Messages are formatted in HTML because it's more forgiving than MarkdownV2
when post titles contain special characters.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

import requests

import config
from src.grouper import PostGroup

logger = logging.getLogger(__name__)

# Telegram limits a single message to 4096 characters
_MAX_MESSAGE_LEN = 4096

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _format_post(index: int, post: dict) -> str:
    """Render a single post as a clickable HTML link."""
    title = html.escape(post["title"])
    link = post["permalink"]

    return f'  {index}. <a href="{link}">{title}</a>'


def _format_group(group: PostGroup) -> str:
    """Render one group header + its posts, with breathing room between items."""
    label = html.escape(group.subreddits_label)
    header = f"🔹 <b>{html.escape(group.name)}</b>  ({label})"
    posts = "\n\n".join(
        _format_post(i + 1, p) for i, p in enumerate(group.posts)
    )
    return f"{header}\n\n{posts}"


def _split_message(text: str) -> list[str]:
    """
    Split a long message into chunks that fit within Telegram's limit.

    Tries to break on double-newlines (between groups) to keep groups intact.
    Falls back to single-newline splits if a single group is too long.
    """
    if len(text) <= _MAX_MESSAGE_LEN:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= _MAX_MESSAGE_LEN:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single paragraph exceeds the limit, hard-split it
            while len(paragraph) > _MAX_MESSAGE_LEN:
                chunks.append(paragraph[:_MAX_MESSAGE_LEN])
                paragraph = paragraph[_MAX_MESSAGE_LEN:]
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def send_digest(groups: list[PostGroup]) -> None:
    """
    Send the digest to Telegram, sending each group as a separate message.

    Raises on HTTP errors so GitHub Actions marks the run as failed.
    """
    url = _TELEGRAM_API.format(token=config.TELEGRAM_BOT_TOKEN)
    today = datetime.now(tz=timezone.utc).strftime("%d %b %Y")

    logger.info("Sending digest (%d groups as separate messages) …", len(groups))

    for i, group in enumerate(groups, 1):
        message = _format_group(group)
        
        # Prepend the general digest title to the very first message
        if i == 1:
            message = f"📰 <b>Reddit Digest — {today}</b>\n\n" + message

        chunks = _split_message(message)

        for chunk_idx, chunk in enumerate(chunks, 1):
            payload = {
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()

        logger.info("Group %d/%d sent.", i, len(groups))
