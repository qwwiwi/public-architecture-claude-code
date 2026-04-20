#!/usr/bin/env python3
"""
claude-telegram-gateway -- Universal Telegram <-> Claude Code router.

Routes Telegram messages to Claude Code CLI sessions per agent.
Each agent gets its own Telegram bot, Claude workspace, and session state.

Features:
- Producer-consumer architecture (OOB commands like /stop handled instantly)
- Markdown -> Telegram HTML conversion
- Voice/audio transcription via Groq Whisper
- Hot memory (rolling journal per agent)
- OpenViking semantic memory push (optional)
- Session management with --resume
- Media handling (photo, video, voice, document, sticker)
- Group chat support with @mention / name detection
- Real-time progress tracking (tool calls, subagent dispatches, TodoWrite plans)
- Forward context: agent sees who forwarded the message
- Message reactions: eyes emoji on received messages
- Inline buttons: send_message_with_buttons + callback query dispatch
- Sticker cache: cached descriptions for repeated stickers
- Webhook API: HTTP endpoint for external message injection
- Per-topic routing: route group-chat topics to specific agents
- Streaming modes: off / partial / progress (configurable per agent)

Usage:
    1. Copy config.example.json -> config.json
    2. Fill in agent config (telegram token, workspace, etc.)
    3. python3 gateway.py

Config structure (config.json):
    {
        "allowlist_user_ids": [123456789],
        "webhook_port": 9090,
        "webhook_token": "your-secret-token",
        "agents": {
            "myagent": {
                "enabled": true,
                "workspace": "/path/to/agent/.claude",
                "model": "sonnet",
                "timeout_sec": 120,
                "streaming_mode": "partial",
                "telegram_bot_token": "123456:AABBccdd...",
                "telegram_bot_token_file": "/path/to/token.txt",
                "groq_api_key": "YOUR_GROQ_API_KEY",
                "groq_api_key_file": "/path/to/groq.key",
                "openviking_url": "http://127.0.0.1:1933",
                "openviking_key_file": "/path/to/ov.key",
                "openviking_account": "default",
                "agent_names": ["myagent", "agent"],
                "topic_routing": {"-1001234567890": ["42", "99"]},
                "env": {"KEY": "value"}
            }
        }
    }

Token resolution order:
- "telegram_bot_token" (direct value in config) takes priority
- "telegram_bot_token_file" (path to file) used as fallback
Same pattern for groq_api_key / groq_api_key_file.
"""
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import fcntl as _fcntl
import random as _random
import re as _re
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor

import requests

import atexit as _atexit

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

# Bounded thread pool for OV pushes (prevents unbounded thread spawning on message bursts)
_OV_POOL = _ThreadPoolExecutor(max_workers=2, thread_name_prefix="ov-push")

# Active claude subprocesses per (agent, chat_id) for /stop command
_ACTIVE_PROCS: dict[tuple[str, int], Any] = {}
_ACTIVE_PROCS_LOCK = threading.Lock()

# Per-agent message queues for producer-consumer architecture
_MSG_QUEUES: dict[str, queue.Queue] = {}

# Per-agent per-chat queues and worker threads for parallel chat processing
_CHAT_QUEUES: dict[str, dict[int, queue.Queue]] = {}
_CHAT_WORKERS: dict[str, dict[int, threading.Thread]] = {}
_CHAT_LOCKS: dict[str, threading.Lock] = {}  # protects _CHAT_QUEUES/_CHAT_WORKERS per agent

# Shutdown event to gracefully stop all threads
_SHUTDOWN_EVENT = threading.Event()

# Out-of-band commands handled instantly by producer thread
_OOB_COMMANDS = frozenset({"/stop", "/cancel", "/status", "/reset", "/new"})


@_atexit.register
def _shutdown_ov_pool() -> None:
    """Graceful drain of pending OV pushes on gateway shutdown."""
    try:
        _OV_POOL.shutdown(wait=True, cancel_futures=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Paths -- relative to working directory (cwd where gateway.py is launched)
# ---------------------------------------------------------------------------

_BASE_DIR = Path.cwd()
LOG_PATH = _BASE_DIR / "gateway.log"
CONFIG_PATH = _BASE_DIR / "config.json"
STATE_DIR = _BASE_DIR / "state"
MEDIA_DIR = _BASE_DIR / "media-inbound"
STICKER_CACHE_PATH = STATE_DIR / "sticker-cache.json"
STATE_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# In-memory sticker description cache (loaded from disk on startup)
_sticker_cache: dict[str, str] = {}
if STICKER_CACHE_PATH.exists():
    try:
        _sticker_cache = json.loads(STICKER_CACHE_PATH.read_text())
    except Exception:
        _sticker_cache = {}


def _save_sticker_cache() -> None:
    try:
        STICKER_CACHE_PATH.write_text(json.dumps(_sticker_cache, ensure_ascii=False))
    except Exception:
        pass


def _get_sticker_description(
    uid: str, emoji: str, set_name: str, local_path: Path | None
) -> str:
    """Get or build sticker description. Cache by file_unique_id."""
    if uid and uid in _sticker_cache:
        return _sticker_cache[uid]

    parts: list[str] = []
    if emoji:
        parts.append(f"emoji {emoji}")
    if set_name:
        parts.append(f"set \"{set_name}\"")
    if local_path:
        parts.append(str(local_path))

    desc = ", ".join(parts) if parts else "sticker (no description)"

    if uid:
        _sticker_cache[uid] = desc
        _save_sticker_cache()

    return desc


# Legacy fallback for Groq key (checked after agent config)
GROQ_KEY_FILE = Path.home() / ".secrets" / "groq-api-key"

TG_MAX_FILE_MB = 20  # Telegram Bot API hard limit
MEDIA_EXTENSIONS = {
    "voice": ".ogg",
    "audio": "",  # keep original
    "video": ".mp4",
    "video_note": ".mp4",
    "photo": ".jpg",
    "document": "",  # keep original
    "sticker": ".webp",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("gateway")


# ---------------------------------------------------------------------------
# Placeholder -- generic, no per-agent pools
# ---------------------------------------------------------------------------

def _media_to_input_type(msg: dict, source_tag: str) -> str:
    """Map Telegram message to input_type for placeholder selection."""
    if source_tag == "forwarded":
        return "forwarded"
    if "voice" in msg or "video_note" in msg or "audio" in msg:
        return "voice"
    if "video" in msg:
        return "video"
    if "photo" in msg:
        return "photo"
    if "document" in msg:
        return "document"
    if "sticker" in msg:
        return "sticker"
    return "text"


def get_placeholder(agent: str, input_type: str = "text") -> str:
    """Pick a generic placeholder for any agent/input_type."""
    _GENERIC: dict[str, list[str]] = {
        "text": ["думаю", "обрабатываю", "анализирую", "работаю", "принял"],
        "voice": ["слушаю голосовое", "транскрибирую", "разбираю речь"],
        "video": ["смотрю видео", "анализирую видео"],
        "photo": ["рассматриваю изображение", "изучаю картинку"],
        "document": ["читаю документ", "изучаю файл"],
        "forwarded": ["изучаю пересланное", "разбираю материал"],
        "sticker": ["принял стикер"],
    }
    pool = _GENERIC.get(input_type) or _GENERIC["text"]
    return _random.choice(pool) + "..."


# ---------------------------------------------------------------------------
# HTML / Markdown utilities
# ---------------------------------------------------------------------------

# HTML parse error detection
_PARSE_ERR_RE = _re.compile(
    r"can't parse entities|parse entities|find end of the entity|unsupported start tag|unexpected end tag",
    _re.IGNORECASE,
)


def escape_html(text: str) -> str:
    """Escape 3 chars for Telegram HTML body. Order matters: & first."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_html_attr(text: str) -> str:
    return escape_html(text).replace('"', "&quot;")


def is_html_parse_error(resp_body: Any) -> bool:
    if not isinstance(resp_body, dict):
        return False
    desc = resp_body.get("description", "") or ""
    return bool(_PARSE_ERR_RE.search(desc))


# Markdown -> Telegram HTML converter
_MD_CODEBLOCK_RE = _re.compile(r"```([a-zA-Z0-9_+\-]*)\n?(.*?)```", _re.DOTALL)
_MD_INLINECODE_RE = _re.compile(r"`([^`\n]+?)`")
_MD_BOLD_RE = _re.compile(r"\*\*([^\*\n]+?)\*\*")
_MD_ITALIC_STAR_RE = _re.compile(r"(?<![\w\*])\*([^\*\n]+?)\*(?!\w)")
# Underscore italic: require whitespace/punctuation boundary to avoid breaking
# identifiers like config_file.py, snake_case, etc.
_MD_ITALIC_UND_RE = _re.compile(r"(?:(?<=\s)|(?<=^)|(?<=[.,;:!?\(\[]))_([^_\n]+?)_(?=\s|$|[.,;:!?\)\]])")
_MD_LINK_RE = _re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_HEADING_RE = _re.compile(r"^(#{1,6})\s+(.+)$", _re.MULTILINE)
_MD_STRIKE_RE = _re.compile(r"~~([^~\n]+?)~~")
_MD_TABLE_RE = _re.compile(
    r"(?:^[ \t]*\|.+\|[ \t]*\n)+"
    r"(?:^[ \t]*\|[-:\s|]+\|[ \t]*\n)?"
    r"(?:^[ \t]*\|.+\|[ \t]*\n)*",
    _re.MULTILINE,
)


def _md_table_to_pre(table_text: str) -> str:
    """Convert a markdown table block into a <pre> block with aligned columns."""
    lines = [ln.strip() for ln in table_text.strip().splitlines()]
    # Filter out separator rows (|---|---|)
    data_lines = [ln for ln in lines if not _re.match(r"^\|[\s\-:|]+\|$", ln)]
    if not data_lines:
        return table_text

    # Parse cells
    rows: list[list[str]] = []
    for ln in data_lines:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return table_text

    # Calculate max width per column
    num_cols = max(len(r) for r in rows)
    col_widths = [0] * num_cols
    for row in rows:
        for i, cell in enumerate(row):
            if i < num_cols:
                col_widths[i] = max(col_widths[i], len(cell))

    # Build aligned output
    out_lines: list[str] = []
    for row in rows:
        parts: list[str] = []
        for i in range(num_cols):
            cell = row[i] if i < len(row) else ""
            parts.append(cell.ljust(col_widths[i]))
        out_lines.append("  ".join(parts).rstrip())

    return "<pre>" + escape_html("\n".join(out_lines)) + "</pre>"


def markdown_to_telegram_html(text: str) -> str:
    """Convert common markdown to Telegram-supported HTML. Safe for already-HTML content."""
    if not text:
        return text

    # Step 1: extract fenced code blocks first (preserve content)
    placeholders: dict[str, str] = {}

    def _save_codeblock(m: _re.Match) -> str:
        lang = m.group(1) or ""
        code = m.group(2).rstrip("\n")
        escaped = escape_html(code)
        if lang:
            html = f'<pre><code class="language-{escape_html_attr(lang)}">{escaped}</code></pre>'
        else:
            html = f"<pre><code>{escaped}</code></pre>"
        key = f"\x00CB{len(placeholders)}\x00"
        placeholders[key] = html
        return key

    text = _MD_CODEBLOCK_RE.sub(_save_codeblock, text)

    # Step 1.5: convert markdown tables to <pre> blocks (before HTML escaping)
    def _save_table(m: _re.Match) -> str:
        html = _md_table_to_pre(m.group(0))
        key = f"\x00TB{len(placeholders)}\x00"
        placeholders[key] = html
        return key

    text = _MD_TABLE_RE.sub(_save_table, text)

    # Step 2: inline code
    def _save_inlinecode(m: _re.Match) -> str:
        code = m.group(1)
        html = f"<code>{escape_html(code)}</code>"
        key = f"\x00IC{len(placeholders)}\x00"
        placeholders[key] = html
        return key

    text = _MD_INLINECODE_RE.sub(_save_inlinecode, text)

    # Step 3: escape HTML special chars in remaining text
    # (but preserve already-present HTML tags the agent might have used)
    # We accept agent's <b>, <i>, <code>, <pre>, <a>, <s>, <tg-spoiler>, <blockquote>
    _SAFE_TAGS = ("b", "i", "s", "code", "pre", "a", "tg-spoiler", "blockquote", "u")
    _TAG_RE = _re.compile(
        r"</?(" + "|".join(_SAFE_TAGS) + r")(?:\s[^>]*)?>", _re.IGNORECASE
    )

    tag_placeholders: dict[str, str] = {}

    def _save_tag(m: _re.Match) -> str:
        key = f"\x00TG{len(tag_placeholders)}\x00"
        tag_placeholders[key] = m.group(0)
        return key

    text = _TAG_RE.sub(_save_tag, text)
    # Now escape
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Restore known tags
    for key, val in tag_placeholders.items():
        text = text.replace(key, val)

    # Step 4: markdown transformations
    text = _MD_HEADING_RE.sub(lambda m: f"<b>{m.group(2)}</b>", text)
    text = _MD_BOLD_RE.sub(r"<b>\1</b>", text)
    text = _MD_STRIKE_RE.sub(r"<s>\1</s>", text)
    text = _MD_ITALIC_STAR_RE.sub(r"<i>\1</i>", text)
    text = _MD_ITALIC_UND_RE.sub(r"<i>\1</i>", text)
    text = _MD_LINK_RE.sub(
        lambda m: f'<a href="{escape_html_attr(m.group(2))}">{m.group(1)}</a>', text
    )

    # Step 5: restore code placeholders
    for key, val in placeholders.items():
        text = text.replace(key, val)

    return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def expand(p: str) -> str:
    return os.path.expanduser(p)


def _resolve_token(cfg: dict, direct_key: str, file_key: str) -> str | None:
    """Resolve a secret from config: direct value first, then file fallback."""
    val = cfg.get(direct_key)
    if val:
        return val.strip()
    fpath = cfg.get(file_key)
    if fpath:
        p = Path(expand(fpath))
        if p.exists():
            return p.read_text().strip()
    return None


def _resolve_telegram_token(cfg: dict) -> str:
    """Resolve Telegram bot token from agent config. Raises if not found."""
    token = _resolve_token(cfg, "telegram_bot_token", "telegram_bot_token_file")
    if not token:
        raise ValueError(
            "No telegram token: set 'telegram_bot_token' or 'telegram_bot_token_file' in agent config"
        )
    return token


def _resolve_groq_key(cfg: dict) -> str | None:
    """Resolve Groq API key: agent config first, then global fallback file."""
    key = _resolve_token(cfg, "groq_api_key", "groq_api_key_file")
    if key:
        return key
    # Global fallback
    if GROQ_KEY_FILE.exists():
        return GROQ_KEY_FILE.read_text().strip()
    return None


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------

_MAX_DOCUMENT_BYTES = 50 * 1024 * 1024  # Telegram sendDocument limit: 50 MB

def tg_api(token: str, method: str, retry: int = 2, **params: Any) -> dict:
    """Telegram API call with retry on 429/5xx/network errors."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    last_exc: Any = None
    for attempt in range(retry + 1):
        try:
            r = requests.post(url, json=params, timeout=30)
            if r.status_code == 429:
                # Rate limit -- honor retry_after if present
                wait = r.json().get("parameters", {}).get("retry_after", 1)
                time.sleep(min(wait, 30))
                continue
            if r.status_code >= 500:
                last_exc = Exception(f"telegram {r.status_code}: {r.text[:200]}")
                time.sleep(1 + attempt)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_exc = e
            if attempt < retry:
                time.sleep(1 + attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    return {}


def _send_one(token: str, chat_id: int, text: str, reply_to: int | None, parse_mode: str | None) -> None:
    """Send single message with HTML parse_mode, fallback to plain on parse error."""
    params: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
        params["allow_sending_without_reply"] = True
    if parse_mode:
        params["parse_mode"] = parse_mode
    try:
        tg_api(token, "sendMessage", **params)
    except requests.HTTPError as e:
        body = None
        try:
            body = e.response.json()
        except Exception:
            pass
        if parse_mode and is_html_parse_error(body):
            # Retry without parse_mode (plain text)
            params.pop("parse_mode", None)
            tg_api(token, "sendMessage", **params)
            return
        raise


def send_message(
    token: str, chat_id: int, text: str, reply_to: int | None = None, html: bool = True
) -> None:
    """Send text to Telegram, chunking by 4000 chars at paragraph boundaries when possible."""
    # Convert markdown -> HTML (if HTML mode)
    if html:
        text = markdown_to_telegram_html(text)

    # Chunk by paragraphs (double newline), fallback to 4000-char slices
    limit = 4000
    if len(text) <= limit:
        chunks = [text]
    else:
        chunks = []
        paragraphs = text.split("\n\n")
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= limit:
                current = current + "\n\n" + p if current else p
            else:
                if current:
                    chunks.append(current)
                if len(p) > limit:
                    # Try splitting by single newline first, then hard split
                    sub_lines = p.split("\n")
                    sub_current = ""
                    for sl in sub_lines:
                        if len(sub_current) + len(sl) + 1 <= limit:
                            sub_current = sub_current + "\n" + sl if sub_current else sl
                        else:
                            if sub_current:
                                chunks.append(sub_current)
                            if len(sl) > limit:
                                for i in range(0, len(sl), limit):
                                    chunks.append(sl[i : i + limit])
                                sub_current = ""
                            else:
                                sub_current = sl
                    if sub_current:
                        chunks.append(sub_current)
                    current = ""
                else:
                    current = p
        if current:
            chunks.append(current)
    parse_mode = "HTML" if html else None
    for chunk in chunks:
        _send_one(token, chat_id, chunk, reply_to, parse_mode)
        reply_to = None  # only first chunk is a reply


def send_chat_action(token: str, chat_id: int, action: str = "typing") -> None:
    try:
        tg_api(token, "sendChatAction", chat_id=chat_id, action=action)
    except Exception as e:
        log.warning(f"sendChatAction failed: {e}")


def set_reaction(
    token: str, chat_id: int, message_id: int, emoji: str = "\U0001f440"
) -> None:
    """Set emoji reaction on a message (ack). Default: eyes emoji."""
    try:
        tg_api(
            token, "setMessageReaction",
            chat_id=chat_id,
            message_id=message_id,
            reaction=json.dumps([{"type": "emoji", "emoji": emoji}]),
        )
    except Exception as e:
        log.debug(f"setMessageReaction failed (non-critical): {e}")


def send_message_with_buttons(
    token: str,
    chat_id: int,
    text: str,
    buttons: list[list[dict[str, str]]],
    reply_to: int | None = None,
    html: bool = True,
) -> dict | None:
    """Send message with inline keyboard buttons.

    Args:
        buttons: 2D list of button rows, each button is {"text": "...", "callback_data": "..."}
                 or {"text": "...", "url": "..."} for URL buttons.
    Returns:
        Telegram API response dict or None on error.
    """
    if html:
        text = markdown_to_telegram_html(text)
    params: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text[:4000],
        "reply_markup": json.dumps({"inline_keyboard": buttons}),
    }
    if reply_to:
        params["reply_to_message_id"] = reply_to
        params["allow_sending_without_reply"] = True
    if html:
        params["parse_mode"] = "HTML"
    try:
        return tg_api(token, "sendMessage", **params)
    except requests.HTTPError as e:
        body = None
        try:
            body = e.response.json()
        except Exception:
            pass
        if html and is_html_parse_error(body):
            params.pop("parse_mode", None)
            return tg_api(token, "sendMessage", **params)
        log.warning(f"send_message_with_buttons failed: {e}")
        return None


def answer_callback_query(
    token: str, callback_query_id: str, text: str = "", show_alert: bool = False
) -> None:
    """Answer a callback query (inline button press)."""
    try:
        tg_api(
            token, "answerCallbackQuery",
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert,
        )
    except Exception as e:
        log.warning(f"answerCallbackQuery failed: {e}")


def send_document(
    token: str,
    chat_id: int,
    file_path: str,
    caption: str | None = None,
    reply_to: int | None = None,
) -> dict:
    """Send a local file to Telegram via sendDocument API.

    Args:
        token: Telegram bot token.
        chat_id: Target chat ID.
        file_path: Absolute path to local file.
        caption: Optional caption (HTML, max 1024 chars).
        reply_to: Optional message ID to reply to.

    Returns:
        Telegram API response dict.
    """
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    data: dict[str, Any] = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:1024]
        data["parse_mode"] = "HTML"
    if reply_to:
        data["reply_to_message_id"] = reply_to
        data["allow_sending_without_reply"] = True
    p = Path(file_path)
    if not p.exists():
        log.warning(f"send_document: file not found: {file_path}")
        return {}
    file_size = p.stat().st_size
    if file_size > _MAX_DOCUMENT_BYTES:
        log.warning(
            f"send_document: file too large"
            f" ({file_size} bytes): {file_path}"
        )
        return {}
    last_exc: Any = None
    for attempt in range(3):
        try:
            with open(p, "rb") as f:
                files = {"document": (p.name, f)}
                r = requests.post(
                    url, data=data, files=files, timeout=120,
                )
            if r.status_code == 429:
                wait = r.json().get(
                    "parameters", {},
                ).get("retry_after", 1)
                time.sleep(min(wait, 30))
                continue
            if r.status_code >= 500:
                last_exc = Exception(
                    f"telegram {r.status_code}: {r.text[:200]}"
                )
                time.sleep(1 + attempt)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_exc = e
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    return {}


# Pending callback handlers: {callback_data_prefix: handler_func}
# Handler signature: handler(token, agent, cfg, callback_query) -> None
_CALLBACK_HANDLERS: dict[str, Any] = {}


def register_callback_handler(prefix: str, handler: Any) -> None:
    """Register a handler for callback_data starting with prefix."""
    _CALLBACK_HANDLERS[prefix] = handler


def dispatch_callback_query(token: str, agent: str, cfg: dict, cq: dict) -> None:
    """Route a callback_query to the appropriate handler."""
    data = cq.get("data", "")
    for prefix, handler in _CALLBACK_HANDLERS.items():
        if data.startswith(prefix):
            try:
                handler(token, agent, cfg, cq)
            except Exception as e:
                log.exception(f"callback handler error ({prefix}): {e}")
                answer_callback_query(token, cq["id"], f"Error: {e}", show_alert=True)
            return
    # No handler matched -- acknowledge silently
    answer_callback_query(token, cq["id"])


# ---------------------------------------------------------------------------
# Group chat: agent name detection
# ---------------------------------------------------------------------------

def _get_agent_names(agent: str, cfg: dict) -> list[str]:
    """Get agent name aliases from config, fallback to [agent]."""
    names = cfg.get("agent_names")
    if names and isinstance(names, list):
        return [n.lower() for n in names]
    return [agent.lower()]


def is_addressed_to_agent(agent: str, msg: dict, bot_username: str | None, cfg: dict | None = None) -> bool:
    """For group chats: check if message explicitly addresses this agent.

    Returns True if:
    - DM (private chat) -- always addressed
    - Group chat AND (@bot_username mentioned OR agent name appears in text)
    """
    chat_type = (msg.get("chat") or {}).get("type", "private")
    if chat_type == "private":
        return True  # DM -- always address

    # Group/supergroup -- need explicit mention or name
    text = (
        msg.get("text") or msg.get("caption")
        or msg.get("_voice_transcript") or ""
    ).lower()
    if not text:
        return False

    # Check @bot_username mention
    if bot_username:
        if f"@{bot_username.lower()}" in text:
            return True

    # Check agent name aliases
    names = _get_agent_names(agent, cfg or {})
    for name in names:
        if name in text:
            return True

    # Check reply-to-bot: if user replied to bot's message
    reply_to = msg.get("reply_to_message") or {}
    reply_from = (reply_to.get("from") or {})
    if reply_from.get("is_bot") and reply_from.get("username", "").lower() == (bot_username or "").lower():
        return True

    return False


# ---------------------------------------------------------------------------
# Message classification
# ---------------------------------------------------------------------------

def classify_source(msg: dict) -> tuple[str, str]:
    """Classify message source. Returns (source_tag, human_label).

    Tags:
    - own_text: user's own typed message (includes caption under photo/video/doc)
    - own_voice: user's voice/video_note (direct speech)
    - forwarded: forwarded from someone else
    - external_media: bare media (photo/video/document) without caption text
    """
    # Forward detection first -- forwarded content is always external source
    if (msg.get("forward_from") or msg.get("forward_from_chat")
            or msg.get("forward_sender_name") or msg.get("forward_origin")):
        origin = msg.get("forward_origin") or {}
        name = (
            (msg.get("forward_from") or {}).get("first_name")
            or (msg.get("forward_from_chat") or {}).get("title")
            or msg.get("forward_sender_name")
            or origin.get("sender_user_name")
            or "unknown"
        )
        return ("forwarded", f"forwarded from: {name}")
    # Voice/video_note = user speaking directly
    if "voice" in msg or "video_note" in msg:
        return ("own_voice", "user voice message")
    # Media with caption = user's own text with attachment
    has_media = any(k in msg for k in ("audio", "video", "photo", "document", "sticker"))
    has_caption = bool(msg.get("caption"))
    if has_media and has_caption:
        return ("own_text", "user text with attachment")
    if has_media:
        return ("external_media", "media attachment from user")
    return ("own_text", "user text")


# ---------------------------------------------------------------------------
# Media handling
# ---------------------------------------------------------------------------

def resolve_media_ref(msg: dict) -> dict | None:
    """Detect media in Telegram message, return {type, file_id, file_name, mime_type, file_size}."""
    if "photo" in msg and msg["photo"]:
        # photo is array of sizes; take largest
        largest = msg["photo"][-1]
        return {
            "type": "photo",
            "file_id": largest.get("file_id"),
            "file_name": None,
            "mime_type": "image/jpeg",
            "file_size": largest.get("file_size", 0),
        }
    for t in ("voice", "audio", "video", "video_note", "document", "sticker"):
        if t in msg:
            obj = msg[t]
            return {
                "type": t,
                "file_id": obj.get("file_id"),
                "file_name": obj.get("file_name"),
                "mime_type": obj.get("mime_type"),
                "file_size": obj.get("file_size", 0),
            }
    return None


def download_telegram_file(token: str, file_id: str, media_type: str, file_name: str | None) -> Path | None:
    """Download file from Telegram Bot API, save to MEDIA_DIR. Returns path or None."""
    try:
        r = tg_api(token, "getFile", file_id=file_id)
        file_info = r.get("result") or {}
        file_path = file_info.get("file_path")
        file_size = file_info.get("file_size", 0)
        if not file_path:
            log.warning(f"getFile: no file_path for {file_id}")
            return None
        if file_size > TG_MAX_FILE_MB * 1024 * 1024:
            log.warning(f"file too big: {file_size} bytes > {TG_MAX_FILE_MB}MB")
            return None
        # Derive local filename
        # Force known extensions for types where Groq/processors are strict
        if media_type == "voice":
            ext = ".ogg"  # Telegram gives .oga but Groq only accepts .ogg/.opus
        elif media_type == "video_note":
            ext = ".mp4"
        else:
            ext = Path(file_path).suffix or MEDIA_EXTENSIONS.get(media_type, "")
        if file_name:
            sanitized = _re.sub(r"[^\w\-. ]", "_", Path(file_name).stem)[:40]
            local_name = f"{sanitized}---{uuid.uuid4()}{ext}"
        else:
            local_name = f"{uuid.uuid4()}{ext}"
        local_path = MEDIA_DIR / local_name
        # Download
        url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        log.info(f"downloaded {media_type} -> {local_path.name} ({file_size} bytes)")
        return local_path
    except Exception as e:
        log.warning(f"download_telegram_file failed: {e}")
        return None


def transcribe_audio(path: Path, agent_cfg: dict | None = None, language: str = "ru") -> str | None:
    """Transcribe audio via Groq Whisper. Returns transcript text or None."""
    key = _resolve_groq_key(agent_cfg or {})
    if not key:
        log.warning("GROQ key missing, skip transcription")
        return None
    try:
        with open(path, "rb") as f:
            files = {"file": (path.name, f, "audio/ogg")}
            data = {
                "model": "whisper-large-v3-turbo",
                "response_format": "text",
                "language": language,
            }
            r = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                files=files,
                data=data,
                timeout=60,
            )
        if r.status_code == 200:
            return r.text.strip()
        log.warning(f"groq transcribe HTTP {r.status_code}: {r.text[:200]}")
        return None
    except Exception as e:
        log.warning(f"groq transcribe failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Telegram message editing / deletion
# ---------------------------------------------------------------------------

def edit_message(token: str, chat_id: int, message_id: int, text: str, html: bool = True) -> None:
    """Edit Telegram message. Silent on 'message not modified'. HTML fallback to plain.
    Retry once on transient network errors (backoff 500ms).
    """
    text = text[:4000]
    params: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if html:
        params["parse_mode"] = "HTML"

    def _try(attempt: int = 0) -> bool:
        try:
            tg_api(token, "editMessageText", **params)
            return True
        except requests.HTTPError as e:
            body = None
            try:
                body = e.response.json()
            except Exception:
                pass
            desc = (body.get("description", "") if isinstance(body, dict) else "").lower()
            if "message is not modified" in desc:
                return True
            if html and is_html_parse_error(body):
                params.pop("parse_mode", None)
                try:
                    tg_api(token, "editMessageText", **params)
                    return True
                except Exception as e2:
                    log.warning(f"editMessageText plain fallback failed: {e2}")
                    return False
            log.warning(f"editMessageText HTTP {e}")
            return False
        except requests.RequestException as e:
            # Network/timeout error -- retry once
            if attempt < 1:
                time.sleep(0.5)
                return _try(attempt + 1)
            log.warning(f"editMessageText network error after retry: {e}")
            return False
        except Exception as e:
            log.warning(f"editMessageText failed: {e}")
            return False

    _try()


def delete_message(token: str, chat_id: int, message_id: int) -> None:
    try:
        tg_api(token, "deleteMessage", chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Commands (/status, /reset, /new, /compact, /stop, /help)
# ---------------------------------------------------------------------------

def _get_workspace(agent: str, cfg: dict) -> str:
    """Get workspace path from agent config."""
    return expand(cfg["workspace"])


def handle_command(token: str, chat_id: int, agent: str, cmd: str, args: str, cfg: dict | None = None) -> bool:
    """Handle /status /reset /new /help commands. Returns True if handled."""
    cfg = cfg or {}
    sid_file = STATE_DIR / f"sid-{agent}-{chat_id}.txt"
    first_file = STATE_DIR / f"sid-{agent}-{chat_id}.first"

    if cmd == "/status":
        workspace = _get_workspace(agent, cfg) if cfg.get("workspace") else None
        core_dir = Path(workspace) / "core" if workspace else None

        hot_kb = decisions_kb = memory_kb = rules_kb = 0.0
        if core_dir:
            hot_file = core_dir / "hot" / "recent.md"
            decisions_file = core_dir / "warm" / "decisions.md"
            memory_file = core_dir / "MEMORY.md"
            rules_file = core_dir / "rules.md"
            hot_kb = hot_file.stat().st_size / 1024 if hot_file.exists() else 0
            decisions_kb = decisions_file.stat().st_size / 1024 if decisions_file.exists() else 0
            memory_kb = memory_file.stat().st_size / 1024 if memory_file.exists() else 0
            rules_kb = rules_file.stat().st_size / 1024 if rules_file.exists() else 0

        if sid_file.exists():
            sid = sid_file.read_text().strip()
            age = time.time() - sid_file.stat().st_mtime
            age_str = f"{int(age/3600)}ч {int((age%3600)/60)}м" if age > 3600 else f"{int(age/60)}м"
            session_extra = ""
            jsonl_dir = Path.home() / ".claude" / "projects"
            for d in jsonl_dir.iterdir() if jsonl_dir.exists() else []:
                jf = d / f"{sid}.jsonl"
                if jf.exists():
                    size_kb = jf.stat().st_size / 1024
                    turns = sum(1 for _ in jf.open())
                    session_extra = f"\nturns: {turns} | {size_kb:.0f} KB"
                    break
            text = (
                f"<b>сессия активна</b>\n"
                f"id: <code>{sid[:8]}...</code>\n"
                f"возраст: {age_str}{session_extra}\n\n"
                f"<b>память</b>\n"
                f"rules: {rules_kb:.1f} KB\n"
                f"warm (decisions): {decisions_kb:.1f} KB\n"
                f"hot (recent): {hot_kb:.1f} KB\n"
                f"cold (MEMORY): {memory_kb:.1f} KB"
            )
        else:
            text = (
                f"<b>сессия пуста</b>\n\n"
                f"следующее сообщение = новая сессия\n\n"
                f"<b>память</b>\n"
                f"rules: {rules_kb:.1f} KB\n"
                f"warm: {decisions_kb:.1f} KB\n"
                f"hot: {hot_kb:.1f} KB\n"
                f"cold: {memory_kb:.1f} KB"
            )
        try:
            tg_api(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception:
            pass
        return True

    if cmd in ("/reset", "/new"):
        force = args.strip().lower() == "force"
        if not sid_file.exists():
            try:
                tg_api(token, "sendMessage", chat_id=chat_id, text="<b>session already empty</b>", parse_mode="HTML")
            except Exception:
                pass
            return True

        old_sid = sid_file.read_text().strip()

        if force:
            sid_file.unlink(missing_ok=True)
            first_file.unlink(missing_ok=True)
            text = (
                f"<b>session reset (force)</b>\n\n"
                f"old: <code>{old_sid[:8]}...</code>\n"
                f"next message = new session"
            )
            try:
                tg_api(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
            except Exception:
                pass
            return True

        try:
            ack = tg_api(token, "sendMessage", chat_id=chat_id,
                         text="<i>handoff: сжимаю контекст...</i>", parse_mode="HTML")
            ack_msg_id = ack.get("result", {}).get("message_id")
        except Exception:
            ack_msg_id = None

        def _do_handoff_reset():
            handoff_prompt = (
                "СИСТЕМА: принц нажал /new — полный handoff перед сбросом сессии.\n"
                "Выполни ВСЕ 3 шага:\n\n"
                "1. HANDOFF: Прочитай core/hot/handoff.md (Read tool). "
                "Перезапиши его (Write tool) — оставь последние 10 записей из текущей сессии "
                "(что делали, что решили, что pending). Формат: '### YYYY-MM-DD HH:MM [тип]\\n**Принц:** ...\\n**Silvana:** ...'\n\n"
                "2. WARM: Прочитай core/warm/decisions.md (Read tool). "
                "Добавь в НАЧАЛО файла новую секцию с сегодняшней датой — "
                "ключевые решения, архитектурные изменения, новые правила из этой сессии. "
                "Не дублируй то что уже есть. Edit tool.\n\n"
                "3. MEMORY: Прочитай MEMORY.md (через auto-memory путь). "
                "Добавь/обнови записи: текущий focus, pending actions, "
                "важные решения которых нет в decisions.md. Edit tool.\n\n"
                "Ответь одной строкой: 'handoff: N в handoff, M в decisions, K в memory'"
            )
            import subprocess as _sp
            workspace = _get_workspace(agent, cfg)
            env = os.environ.copy()
            env["PATH"] = f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
            for k, v in (cfg.get("env") or {}).items():
                env[k] = v
            summary = "(не получен)"
            try:
                r = _sp.run(
                    ["claude", "-p", handoff_prompt, "--model", "sonnet",
                     "--output-format", "text", "--permission-mode", "bypassPermissions",
                     "--resume", old_sid],
                    cwd=workspace, env=env, capture_output=True, text=True, timeout=120,
                )
                summary = (r.stdout or r.stderr or "").strip()[:400]
            except Exception as e:
                summary = f"(ошибка handoff: {e})"
            sid_file.unlink(missing_ok=True)
            first_file.unlink(missing_ok=True)
            final_text = (
                f"<b>новая сессия</b>\n\n"
                f"старая: <code>{old_sid[:8]}...</code>\n"
                f"{escape_html(summary)}\n\n"
                f"следующее сообщение = свежий контекст"
            )
            if ack_msg_id:
                edit_message(token, chat_id, ack_msg_id, final_text)
            else:
                try:
                    tg_api(token, "sendMessage", chat_id=chat_id, text=final_text, parse_mode="HTML")
                except Exception:
                    pass

        import threading as _th
        _th.Thread(target=_do_handoff_reset, daemon=True).start()
        return True

    if cmd == "/compact":
        if not sid_file.exists():
            try:
                tg_api(token, "sendMessage", chat_id=chat_id, text="<b>no session</b> -- nothing to compact", parse_mode="HTML")
            except Exception:
                pass
            return True

        sid = sid_file.read_text().strip()
        try:
            ack = tg_api(token, "sendMessage", chat_id=chat_id, text="<i>compacting hot -> warm/decisions.md...</i>", parse_mode="HTML")
            ack_msg_id = ack.get("result", {}).get("message_id")
        except Exception:
            ack_msg_id = None

        def _do_compact():
            today = time.strftime("%Y-%m-%d")
            compact_prompt = (
                f"SYSTEM: manual hot->warm compact.\n"
                f"1. Read core/hot/recent.md (Read tool).\n"
                f"2. Extract key facts from last 24h and ADD to beginning of core/warm/decisions.md:\n"
                f"## {today}\n- fact 1\n- fact 2\n\n"
                f"3. Trim hot/recent.md: keep last 24h.\n"
                f"Extract: new preferences, decisions, pending actions, patterns. "
                f"Skip duplicates.\n"
                f"Reply: 'compact: N added, hot trimmed'."
            )
            import subprocess as _sp
            workspace = _get_workspace(agent, cfg)
            env = os.environ.copy()
            env["PATH"] = f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
            for k, v in (cfg.get("env") or {}).items():
                env[k] = v
            reply = "(timeout)"
            try:
                r = _sp.run(
                    ["claude", "-p", compact_prompt, "--model", "sonnet",
                     "--output-format", "text", "--permission-mode", "bypassPermissions",
                     "--resume", sid],
                    cwd=workspace, env=env, capture_output=True, text=True, timeout=180,
                )
                reply = (r.stdout or r.stderr or "").strip()[:400]
            except Exception as e:
                reply = f"error: {str(e)[:200]}"
            final_text = f"<b>compact done</b>\n\n<i>{escape_html(reply)}</i>"
            if ack_msg_id:
                edit_message(token, chat_id, ack_msg_id, final_text)
            else:
                try:
                    tg_api(token, "sendMessage", chat_id=chat_id, text=final_text, parse_mode="HTML")
                except Exception:
                    pass

        import threading as _th
        _th.Thread(target=_do_compact, daemon=True).start()
        return True

    if cmd in ("/stop", "/cancel"):
        with _ACTIVE_PROCS_LOCK:
            proc = _ACTIVE_PROCS.get((agent, chat_id))
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
                text = "<b>stopped</b>\n\n<i>agent interrupted current task</i>"
            except Exception as e:
                text = f"<b>stop error</b>: {escape_html(str(e)[:100])}"
        else:
            text = "<b>nothing to stop</b> -- agent is idle"
        try:
            tg_api(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception:
            pass
        return True

    if cmd == "/help":
        text = (
            "<b>gateway commands</b>\n\n"
            "<code>/stop</code> or <code>/cancel</code> -- stop current agent task\n"
            "<code>/status</code> -- session and memory status\n"
            "<code>/reset</code> -- reset session (saves important to MEMORY)\n"
            "<code>/reset force</code> -- reset without saving\n"
            "<code>/compact</code> -- manual memory compaction\n"
            "<code>/help</code> -- this help\n\n"
            "<i>auto-compact: daily 05:00 UTC</i>"
        )
        try:
            tg_api(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception:
            pass
        return True

    return False


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def session_id_for(agent: str, chat_id: int) -> str:
    """Stable UUID per (agent, chat). Persisted on disk for --resume."""
    f = STATE_DIR / f"sid-{agent}-{chat_id}.txt"
    if f.exists():
        return f.read_text().strip()
    sid = str(uuid.uuid4())
    f.write_text(sid)
    return sid


def read_latest_memory_section(agent: str, cfg: dict) -> str:
    """Read latest section from core/MEMORY.md for post-reset injection."""
    workspace = _get_workspace(agent, cfg)
    mem_file = Path(workspace) / "core" / "MEMORY.md"
    if not mem_file.exists():
        return ""
    try:
        content = mem_file.read_text()
        # Find all ## sections and return the last one
        import re as _r
        matches = list(_r.finditer(r'^## .+$', content, _r.MULTILINE))
        if not matches:
            return content[:2000]
        last_start = matches[-1].start()
        # Read until next section or EOF
        return content[last_start:][:2000]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Claude invocation
# ---------------------------------------------------------------------------

def invoke_claude(
    agent: str, cfg: dict, chat_id: int, user_text: str
) -> tuple[str, int, int, list[str]]:
    """Run claude -p --resume <sid> and return (response_text, duration_ms, success, written_files)."""
    sid = session_id_for(agent, chat_id)
    workspace = _get_workspace(agent, cfg)
    model = cfg.get("model", "sonnet")

    env = os.environ.copy()
    env["PATH"] = f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    env.setdefault("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "400000")
    for k, v in cfg.get("env", {}).items():
        env[k] = v

    # Use --resume if session exists, --session-id for first turn
    sid_file = STATE_DIR / f"sid-{agent}-{chat_id}.first"
    is_first = not sid_file.exists()

    # Post-reset: inject latest MEMORY.md section so agent knows what was saved
    if is_first:
        latest_memory = read_latest_memory_section(agent, cfg)
        if latest_memory:
            user_text = (
                f"[after reset, latest entry in MEMORY.md]:\n{latest_memory}\n\n"
                f"[current user message]:\n{user_text}"
            )

    cmd = [
        "claude",
        "-p",
        user_text,
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--input-format",
        "text",
        "--verbose",
        "--permission-mode",
        "bypassPermissions",
    ]

    # Inject system reminder via --append-system-prompt (if configured)
    active_reminder = cfg.get("_active_system_reminder", "")
    if active_reminder:
        cmd.extend(["--append-system-prompt", active_reminder])

    if is_first:
        cmd.extend(["--session-id", sid])
    else:
        cmd.extend(["--resume", sid])

    timeout_sec = cfg.get("timeout_sec", 120)
    typing_cb = cfg.get("_typing_refresh_cb")
    status_cb = cfg.get("_status_update_cb")  # (status_text: str) -> None
    streaming_mode = cfg.get("streaming_mode", "partial")  # off | partial | progress
    # In "off" mode, disable status updates (no edit-in-place preview)
    if streaming_mode == "off":
        status_cb = None
    # Always create tracker for file tracking (sendDocument), even without status display
    tracker = _TaskBoundaryTracker(status_cb)
    t0 = time.time()
    last_activity = t0  # heartbeat: reset on every event from Claude
    last_typing = 0.0
    final_text = ""

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )
        # Mark session as registered immediately after Popen —
        # CLI already owns the session-id at this point
        if is_first:
            sid_file.touch()
        # Register for /stop command
        with _ACTIVE_PROCS_LOCK:
            _ACTIVE_PROCS[(agent, chat_id)] = proc

        # Use select on proc.stdout for line-by-line reading with timeout
        import select as _select
        stdout_fd = proc.stdout.fileno() if proc.stdout else None
        buffer = ""

        while True:
            # Heartbeat timeout: kill only if no events for timeout_sec
            now = time.time()
            idle = now - last_activity
            if idle > timeout_sec:
                proc.kill()
                proc.communicate()
                dur_ms = int((now - t0) * 1000)
                log.error(
                    f"claude idle timeout after {idle:.0f}s silence "
                    f"(total {dur_ms}ms, limit={timeout_sec}s)"
                )
                return (
                    f"[gateway error: claude idle {int(idle)}s -- no activity]",
                    dur_ms,
                    0,
                    [],
                )

            # Refresh typing every 2s
            if time.time() - last_typing > 2:
                if typing_cb:
                    try:
                        typing_cb()
                    except Exception:
                        pass
                last_typing = time.time()

            # Read with timeout
            if stdout_fd is not None:
                ready, _, _ = _select.select([stdout_fd], [], [], 1.0)
                if ready:
                    line = proc.stdout.readline()
                    if not line:
                        # EOF -- process done
                        break
                    buffer += line
                    # Parse completed lines
                    while "\n" in buffer:
                        jline, buffer = buffer.split("\n", 1)
                        jline = jline.strip()
                        if not jline:
                            continue
                        try:
                            event = json.loads(jline)
                        except json.JSONDecodeError:
                            continue
                        last_activity = time.time()  # heartbeat: Claude is alive
                        _handle_stream_event(event, tracker)
                        # Capture final result text
                        if event.get("type") == "result":
                            final_text = event.get("result") or final_text
                else:
                    # No output yet -- check if process done
                    if proc.poll() is not None:
                        # Drain remaining
                        remaining = proc.stdout.read() if proc.stdout else ""
                        buffer += remaining
                        for jline in (buffer.strip().split("\n") if buffer.strip() else []):
                            jline = jline.strip()
                            if not jline:
                                continue
                            try:
                                event = json.loads(jline)
                                _handle_stream_event(event, tracker)
                                if event.get("type") == "result":
                                    final_text = event.get("result") or final_text
                            except json.JSONDecodeError:
                                pass
                        break

        proc.wait()
        dur_ms = int((time.time() - t0) * 1000)
        if proc.returncode != 0:
            stderr = proc.stderr.read() if proc.stderr else ""
            log.error(f"claude exit {proc.returncode}: {stderr[:500]}")
            if "already in use" in stderr:
                sid_file.touch()
                log.warning(f"auto-recovery: touched {sid_file.name} after 'already in use'")
            return (f"[gateway error: claude exit {proc.returncode}]", dur_ms, 0, [])
        return (
            final_text.strip(), dur_ms, 1,
            tracker.written_files if tracker else [],
        )
    except Exception as e:
        dur_ms = int((time.time() - t0) * 1000)
        log.exception(f"claude invoke failed: {e}")
        return (f"[gateway error: {e}]", dur_ms, 0, [])
    finally:
        with _ACTIVE_PROCS_LOCK:
            _ACTIVE_PROCS.pop((agent, chat_id), None)


# ---------------------------------------------------------------------------
# Progress tracking (subagent labels, tool tags, status tracker)
# ---------------------------------------------------------------------------

SUBAGENT_LABELS = {
    "researcher": "searching and verifying sources",
    "content-writer": "writing draft",
    "content-orchestrator": "preparing content",
    "firebase-auditor": "auditing data",
    "code-reviewer": "code review",
    "general-purpose": "running research",
    "Explore": "exploring structure",
    "Plan": "building plan",
    "statusline-setup": "setting up status",
    "claude-code-guide": "checking docs",
}

# ASCII tool tags for real-time tool call display (NO emoji)
TOOL_TAGS: dict[str, str] = {
    "Read": "[R]",
    "Write": "[W]",
    "Edit": "[W]",
    "MultiEdit": "[W]",
    "Bash": "[B]",
    "Grep": "[G]",
    "Glob": "[G]",
    "WebFetch": "[F]",
    "WebSearch": "[S]",
    "Agent": "[A]",
    "TodoWrite": "[T]",
}
_TOOL_TAG_DEFAULT = "[.]"


def _summarize_tool_input(name: str, tinput: dict) -> str:
    """Extract a short human-readable summary of tool invocation."""
    s = ""
    if name in ("Read", "Write", "Edit", "MultiEdit"):
        fp = tinput.get("file_path") or tinput.get("path") or ""
        parts = fp.replace("\\", "/").rsplit("/", 2)
        s = "/".join(parts[-2:]) if len(parts) >= 2 else fp
    elif name == "Bash":
        s = (tinput.get("command") or "")[:40]
    elif name == "Grep":
        s = tinput.get("pattern") or ""
        if s:
            s = f'"{s}"'
    elif name == "Glob":
        s = tinput.get("pattern") or ""
        if s:
            s = f'"{s}"'
    elif name == "Agent":
        s = tinput.get("subagent_type") or tinput.get("description") or ""
    elif name == "WebFetch":
        url = tinput.get("url") or ""
        try:
            from urllib.parse import urlparse
            s = urlparse(url).netloc or url[:40]
        except Exception:
            s = url[:40]
    elif name == "WebSearch":
        s = (tinput.get("query") or "")[:40]
    else:
        s = str(tinput)[:30] if tinput else ""
    return escape_html(s[:40])


def _mask_secrets(s: str) -> str:
    """Mask IPs, URLs, tokens, secret paths in status messages for Telegram."""
    import re
    # Mask IPv4 addresses: 1.2.3.4 -> 1.***.***4
    s = re.sub(
        r'\b(\d{1,3})\.\d{1,3}\.\d{1,3}\.(\d{1,3})\b',
        r'\1.***.***.\2', s,
    )
    # Mask secret paths: ~/.secrets/... or /secrets/...
    s = re.sub(r'(~/?\.\w+/)secrets/\S+', r'\1secrets/***', s)
    # Mask API tokens/keys (long alphanumeric strings 20+ chars)
    s = re.sub(r'\b([A-Za-z0-9_-]{4})[A-Za-z0-9_-]{16,}([A-Za-z0-9_-]{4})\b', r'\1***\2', s)
    # Mask bot tokens: 1234567890:AAxx... -> 123***:AA***
    s = re.sub(r'\b(\d{3})\d{7,}:(AA\w{2})\w+', r'\1***:\2***', s)
    # Mask Supabase project URLs
    def _mask_host(m: re.Match) -> str:
        host = m.group(0)
        parts = host.split('.')
        if len(parts[0]) > 8:
            parts[0] = parts[0][:4] + '*****' + parts[0][-4:]
        if len(parts) > 1 and len(parts[-2]) > 5:
            parts[-2] = parts[-2][:4] + '***'
        return '.'.join(parts)
    s = re.sub(r'[a-z0-9]{10,}\.supabase\.co', _mask_host, s)
    return s


def _code(s: str) -> str:
    """Wrap text in <code> tags, escaping content."""
    return f"<code>{escape_html(s)}</code>"


def _humanize_tool(tname: str, tinput: dict) -> str | None:
    """Convert Claude tool invocation into human-readable status line (HTML)."""
    if tname == "Agent":
        sub = tinput.get("subagent_type", "?")
        label = SUBAGENT_LABELS.get(sub, f"running {escape_html(sub)}")
        return f"<b>{escape_html(label)}</b>"
    if tname == "Bash":
        cmd = (tinput.get("command") or "").strip()
        if cmd.startswith("curl"):
            return "calling API"
        if cmd.startswith("git"):
            return "git command"
        if cmd.startswith(("cat ", "tail ", "head ", "ls ", "grep ")):
            return "reading files"
        return f"running: {_code(_mask_secrets(cmd[:60]))}"
    if tname == "Read":
        path = tinput.get("file_path") or ""
        name = path.split("/")[-1] if path else ""
        return f"reading {_code(name)}" if name else "reading file"
    if tname == "Write":
        path = tinput.get("file_path") or ""
        name = path.split("/")[-1] if path else ""
        return f"creating {_code(name)}" if name else "creating file"
    if tname == "Edit":
        path = tinput.get("file_path") or ""
        name = path.split("/")[-1] if path else ""
        return f"editing {_code(name)}" if name else "editing file"
    if tname == "Glob":
        p = tinput.get("pattern") or ""
        return f"searching files: {_code(p[:40])}" if p else "searching files"
    if tname == "Grep":
        p = tinput.get("pattern") or ""
        return f"searching code: {_code(p[:40])}" if p else "searching code"
    if tname == "WebFetch":
        url = tinput.get("url") or ""
        return f"fetching web: {_code(url[:60])}"
    if tname == "WebSearch":
        q = tinput.get("query") or ""
        return f"web search: <i>{escape_html(q[:60])}</i>"
    if tname == "TodoWrite":
        return None  # handled specially
    return None


def _format_todos(todos: list) -> str | None:
    """Format TodoWrite list as HTML checklist."""
    if not todos:
        return None
    lines = []
    for t in todos[:8]:
        status = t.get("status", "pending")
        content = escape_html((t.get("content") or t.get("subject") or "")[:60])
        if status == "completed":
            lines.append(f"  [x] <s>{content}</s>")
        elif status == "in_progress":
            lines.append(f"  [>] <b>{content}</b>")
        else:
            lines.append(f"  [ ] {content}")
    if len(todos) > 8:
        lines.append(f"  ... +{len(todos) - 8} more")
    return "<b>plan:</b>\n" + "\n".join(lines)


class _StatusTracker:
    """Tracks assistant stream events and emits structured progress."""
    def __init__(self, status_cb):
        self.status_cb = status_cb
        self.step_num = 0
        self.current_subagent = None  # set when inside Agent tool turn
        self.lines: list[str] = []

    def _emit(self, line: str) -> None:
        self.lines.append(line)
        if self.status_cb:
            self.status_cb("\n".join(self.lines))

    def handle_event(self, event: dict) -> None:
        etype = event.get("type")
        if etype == "assistant":
            content = (event.get("message") or {}).get("content") or []
            for block in content:
                btype = block.get("type")
                if btype == "tool_use":
                    tname = block.get("name", "")
                    tinput = block.get("input") or {}
                    if tname == "TodoWrite":
                        todos = tinput.get("todos") or []
                        formatted = _format_todos(todos)
                        if formatted:
                            self._emit(formatted)
                        continue
                    line = _humanize_tool(tname, tinput)
                    if not line:
                        continue
                    if tname == "Agent":
                        sub = tinput.get("subagent_type", "?")
                        self.current_subagent = sub
                        self.step_num += 1
                        self._emit(f"<b>{self.step_num}.</b> {line}")
                    else:
                        if self.current_subagent:
                            self._emit(f"   <i>. {line}</i>")
                        else:
                            self.step_num += 1
                            self._emit(f"<b>{self.step_num}.</b> {line}")
        elif etype == "user":
            # tool_result event -- subagent may have finished
            content = (event.get("message") or {}).get("content") or []
            for block in content:
                if block.get("type") == "tool_result":
                    # Heuristic: if previous step was Agent, close the subagent context
                    if self.current_subagent:
                        self.current_subagent = None


def _handle_stream_event(event: dict, tracker: Any) -> None:
    """Pass event to the status tracker."""
    if tracker:
        tracker.handle_event(event)


def _progress_bar(done: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return ""
    pct = min(100, int(done * 100 / total))
    filled = int(width * done / total)
    bar = "\u25b0" * filled + "\u25b1" * (width - filled)
    return f"{bar} {pct}%"


# File extensions that gateway can send as Telegram documents
SENDABLE_EXTENSIONS = {
    ".html", ".pdf", ".png", ".jpg", ".jpeg", ".csv", ".svg",
    ".pptx", ".ppt", ".xlsx", ".xls", ".docx", ".doc",
    ".zip", ".tar", ".gz", ".json", ".txt", ".py", ".md",
}


class _TaskBoundaryTracker:
    """Progress tracker: task boundaries + subagent dispatches.
    Clean display: thinking + plan + subagent steps.
    Individual tool calls (Read/Edit/Bash) collapsed to single activity line.

    Format:
      working -- 45s
      <thinking snippet>

      plan:
      [x] completed task
      [>] in-progress task
      [ ] pending task
      ▰▰▰▰▰▱▱▱▱▱ 50%

      steps:
       1 | researcher -- done
       2 | content-writer  <- now
       3 | delivery
    """
    def __init__(self, status_cb):
        self.status_cb = status_cb
        self.todos: list[dict] = []
        self.dispatches: list[dict] = []  # [{label, desc, status, summary}]
        self.pending_agents: dict[str, int] = {}  # tool_use_id -> dispatch index
        self.tool_calls: list[dict] = []  # [{tag, name, detail}] last N tool calls
        self._thinking: str = ""  # last thinking block, truncated to 3-4 lines
        self._start_time: float = time.time()
        self._last_tool_render: float = 0.0
        self.written_files: list[str] = []  # file paths from Write tool_use

    def _render(self) -> None:
        if not self.status_cb:
            return
        elapsed = int(time.time() - self._start_time)
        lines = [f"working -- {elapsed}s"]
        if self._thinking:
            lines.append("")
            lines.append(self._thinking)
        if self.tool_calls:
            lines.append("")
            lines.append(self._render_activity())
        if self.todos:
            lines.append("")
            lines.extend(self._render_todos())
        if self.dispatches:
            lines.append("")
            lines.extend(self._render_dispatches())
        body = "\n".join(lines).strip()
        if body:
            self.status_cb(f"<pre>{escape_html(body)}</pre>")

    def _render_activity(self) -> str:
        """Single compact activity line instead of listing every tool call."""
        if not self.tool_calls:
            return ""
        last = self.tool_calls[-1]
        name = last["name"]
        total = len(self.tool_calls)
        ACTIVITY_LABELS = {
            "Read": "reading files",
            "Write": "writing files",
            "Edit": "editing files",
            "MultiEdit": "editing files",
            "Bash": "running commands",
            "Grep": "searching code",
            "Glob": "searching files",
            "WebFetch": "fetching web",
            "WebSearch": "web search",
            "ToolSearch": "loading tools",
            "Skill": "running skill",
            "NotebookEdit": "editing notebook",
        }
        label = ACTIVITY_LABELS.get(name, name.lower())
        return f"▸ {label} ({total})"

    def _render_todos(self) -> str:
        done = sum(1 for t in self.todos if t.get("status") == "completed")
        total = len(self.todos)
        completed = [t for t in self.todos if t.get("status") == "completed"]
        in_progress = [t for t in self.todos if t.get("status") == "in_progress"]
        pending = [t for t in self.todos if t.get("status") == "pending"]
        visible: list[tuple[dict, str]] = []
        if completed:
            visible.append((completed[-1], "completed"))
        if done > 1:
            visible.insert(0, ({"content": f"... +{done - 1} done"}, "skip"))
        for t in in_progress:
            visible.append((t, "in_progress"))
        for t in pending[:2]:
            visible.append((t, "pending"))
        if len(pending) > 2:
            visible.append(({"content": f"... +{len(pending) - 2} more"}, "skip"))
        lines = [_progress_bar(done, total)]
        for t, st in visible:
            content = (t.get("content") or "")[:60]
            if st == "skip":
                lines.append(f"  {content}")
            elif st == "completed":
                lines.append(f"  x {content}")
            elif st == "in_progress":
                lines.append(f"  > {content}")
            else:
                lines.append(f"    {content}")
        return lines

    def _render_dispatches(self) -> list[str]:
        total = len(self.dispatches)
        single = total == 1
        lines: list[str] = [] if single else ["steps:"]
        for i, d in enumerate(self.dispatches[-4:], start=max(1, total - 3)):
            label = d["label"]
            status = d["status"]
            if single:
                if status == "done":
                    summary = (d.get("summary", "") or "")[:30]
                    marker = f" -- {summary}" if summary else ""
                    lines.append(f"x {label}{marker}")
                elif status == "running":
                    desc = (d.get("desc", "") or "")[:40]
                    desc_part = f" -- {desc}" if desc else ""
                    lines.append(f"> {label}{desc_part}")
            else:
                if status == "done":
                    summary = (d.get("summary", "") or "")[:30]
                    marker = f" -- {summary}" if summary else ""
                    lines.append(f" {i:>2} | x {label}{marker}")
                elif status == "running":
                    desc = (d.get("desc", "") or "")[:40]
                    desc_part = f" -- {desc}" if desc else ""
                    lines.append(f" {i:>2} | > {label}{desc_part}")
                else:
                    lines.append(f" {i:>2} |   {label}")
        done = sum(1 for d in self.dispatches if d["status"] == "done")
        if total > 1:
            lines.append(_progress_bar(done, total))
        return lines

    @staticmethod
    def _truncate_thinking(text: str, max_lines: int = 2, max_chars: int = 140) -> str:
        lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
        result = "\n".join(lines[-max_lines:])
        if len(result) > max_chars:
            result = result[:max_chars].rsplit(" ", 1)[0] + "..."
        return result

    def handle_event(self, event: dict) -> None:
        etype = event.get("type")
        if etype == "assistant":
            content = (event.get("message") or {}).get("content") or []
            for block in content:
                if block.get("type") == "thinking":
                    raw = block.get("thinking") or ""
                    if raw.strip():
                        self._thinking = self._truncate_thinking(raw)
                        self._render()
                    continue
                if block.get("type") != "tool_use":
                    continue
                tname = block.get("name", "")
                tinput = block.get("input") or {}
                tuid = block.get("id", "")
                # Track every tool call for real-time display
                tag = TOOL_TAGS.get(tname, _TOOL_TAG_DEFAULT)
                detail = _summarize_tool_input(tname, tinput)
                display_detail = f"{tname.lower()} {detail}" if detail else ""
                self.tool_calls.append({"tag": tag, "name": tname, "detail": display_detail})
                # Keep last 10 tool calls
                if len(self.tool_calls) > 10:
                    self.tool_calls = self.tool_calls[-10:]
                # Track written files for sendDocument
                if tname == "Write":
                    fp = tinput.get("file_path", "")
                    if fp:
                        ext = Path(fp).suffix.lower()
                        if ext in SENDABLE_EXTENSIONS:
                            self.written_files.append(fp)
                if tname == "TodoWrite":
                    self.todos = tinput.get("todos") or []
                    self._render()
                elif tname == "Agent":
                    sub = tinput.get("subagent_type", "?")
                    desc = (tinput.get("description") or "")[:60]
                    label = SUBAGENT_LABELS.get(sub, sub)
                    idx = len(self.dispatches)
                    self.dispatches.append({
                        "label": label, "desc": desc, "status": "running", "summary": "",
                    })
                    self.pending_agents[tuid] = idx
                    self._render()
                else:
                    now = time.time()
                    if now - self._last_tool_render >= 5.0:
                        self._last_tool_render = now
                        self._render()
        elif etype == "user":
            # tool_result for Agent = subagent finished
            content = (event.get("message") or {}).get("content") or []
            for block in content:
                if block.get("type") != "tool_result":
                    continue
                tuid = block.get("tool_use_id", "")
                if tuid in self.pending_agents:
                    idx = self.pending_agents.pop(tuid)
                    if idx < len(self.dispatches):
                        # Extract short summary
                        raw = block.get("content")
                        summary = ""
                        if isinstance(raw, str):
                            summary = raw
                        elif isinstance(raw, list):
                            for c in raw:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    summary = c.get("text", "")
                                    break
                        first_line = next((ln for ln in summary.split("\n") if ln.strip()), "")
                        self.dispatches[idx]["status"] = "done"
                        self.dispatches[idx]["summary"] = first_line
                    self._render()


# ---------------------------------------------------------------------------
# Hot memory
# ---------------------------------------------------------------------------

HOT_SIZE_THRESHOLD = 15000  # chars, triggers compaction signal


def append_to_hot_memory(agent: str, cfg: dict, user_text: str, agent_response: str, source_tag: str) -> None:
    """Append lightweight turn summary to agent's hot/recent.md rolling journal.
    Uses fcntl.LOCK_EX to prevent interleaved writes from concurrent chat handlers.
    Emergency trim if file exceeds 20KB.
    """
    workspace = _get_workspace(agent, cfg)
    hot_file = Path(workspace) / "core" / "hot" / "recent.md"
    if not hot_file.parent.exists():
        return
    try:
        ts = time.strftime("%Y-%m-%d %H:%M")
        u_snippet = (user_text or "").replace("\n", " ")[:200]
        a_snippet = (agent_response or "(inline)").replace("\n", " ")[:200]
        entry = (
            f"\n### {ts} [{source_tag}]\n"
            f"**User:** {u_snippet}\n"
            f"**{agent.capitalize()}:** {a_snippet}\n"
        )
        # Atomic append with file lock
        with open(hot_file, "a") as f:
            _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
            try:
                f.write(entry)
                f.flush()
            finally:
                _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)

        # Emergency trim if >20KB (compact failed to run or burst of messages)
        size = hot_file.stat().st_size
        if size > 20480:
            log.warning(f"[hot] {agent} recent.md {size}B -- emergency trim")
            # Keep last ~100 entries (roughly last 2-3 days)
            lines = hot_file.read_text().split("\n")
            # Find cutoff -- keep last 600 lines (entries are 4 lines each, 600/4=150 entries)
            if len(lines) > 600:
                header = "# Hot memory -- last 24h rolling journal\n"
                kept = lines[-600:]
                # Find first entry header to avoid truncated entry at top
                for i, ln in enumerate(kept):
                    if ln.startswith("### "):
                        kept = kept[i:]
                        break
                with open(hot_file, "w") as f:
                    _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
                    try:
                        f.write(header + "\n" + "\n".join(kept))
                    finally:
                        _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)
    except Exception as e:
        log.warning(f"[hot] append failed: {e}")


# ---------------------------------------------------------------------------
# OpenViking semantic memory (optional)
# ---------------------------------------------------------------------------

def push_to_openviking(agent: str, cfg: dict, user_text: str, agent_response: str, chat_id: int) -> None:
    """Push conversation turn to OpenViking for semantic memory extraction.
    Fire-and-forget in background thread."""
    ov_url = cfg.get("openviking_url")
    if not ov_url:
        return
    ov_key_file = cfg.get("openviking_key_file")
    if not ov_key_file:
        return
    key_path = Path(expand(ov_key_file))
    if not key_path.exists():
        return
    key = key_path.read_text().strip()
    ov_account = cfg.get("openviking_account", "default")
    headers = {
        "X-API-Key": key,
        "X-OpenViking-Account": ov_account,
        "X-OpenViking-User": agent,
        "Content-Type": "application/json",
    }
    base = f"{ov_url.rstrip('/')}/api/v1"
    sid = None
    try:
        # Create session
        r = requests.post(f"{base}/sessions", headers=headers, json={}, timeout=10)
        if r.status_code != 200:
            log.warning(f"[ov] create session failed: {r.status_code}")
            return
        sid = r.json().get("result", {}).get("session_id")
        if not sid:
            return
        # user_text already has [source:...] prefix from process_update
        ts = time.strftime("%Y-%m-%d %H:%M")
        # Anti-pollution guard: strong instruction to OV LLM about forwarded content
        if "[source:forwarded" in user_text:
            guard = (
                "\n[extraction hint: this content was FORWARDED to the user from someone else. "
                "Do NOT extract as user's own preferences. Only extract as events/cases/entities about the third-party source.]\n"
            )
        elif "[source:external_media" in user_text:
            guard = (
                "\n[extraction hint: this is external media the user is sharing, not their own words. "
                "Do NOT extract as user's preferences.]\n"
            )
        else:
            guard = ""
        meta_prefix = f"[chat:{chat_id} agent:{agent} at {ts}]{guard}\n"
        requests.post(
            f"{base}/sessions/{sid}/messages",
            headers=headers,
            json={"role": "user", "content": meta_prefix + user_text[:3000]},
            timeout=10,
        )
        if agent_response:
            requests.post(
                f"{base}/sessions/{sid}/messages",
                headers=headers,
                json={"role": "assistant", "content": agent_response[:3000]},
                timeout=10,
            )
        # Extract memories (runs LLM for structured extraction)
        ext = requests.post(f"{base}/sessions/{sid}/extract", headers=headers, json={}, timeout=60)
        extracted = ext.json().get("result", []) if ext.status_code == 200 else []
        log.info(f"[ov] extracted {len(extracted)} memories for {agent}/{chat_id}")
    except Exception as e:
        log.warning(f"[ov] push failed: {e}")
    finally:
        # Always clean up session to prevent leaks
        if sid:
            try:
                requests.delete(f"{base}/sessions/{sid}", headers=headers, timeout=5)
            except Exception:
                pass


def _auto_transcribe_group_voice(
    agent: str, cfg: dict, token: str, msg: dict
) -> None:
    """Auto-transcribe voice/audio/video_note in allowlisted groups.

    Downloads the file, transcribes via Groq Whisper, and replies with
    the transcript as italic HTML. Fire-and-forget via _OV_POOL.
    Does NOT interfere with normal message processing pipeline.
    """
    try:
        voice = (
            msg.get("voice")
            or msg.get("audio")
            or msg.get("video_note")
        )
        if not voice:
            return
        file_id = voice["file_id"]

        # Download using existing helper
        local_path = download_telegram_file(
            token, file_id, "voice", None
        )
        if not local_path:
            log.warning(
                f"[{agent}] auto-transcribe: download failed"
            )
            return

        # Transcribe using existing Groq Whisper helper
        transcript = transcribe_audio(local_path, agent_cfg=cfg)
        if not transcript or not transcript.strip():
            log.info(
                f"[{agent}] auto-transcribe: empty transcript"
            )
            return

        # Reply to the original voice message with italic transcript
        chat_id = msg["chat"]["id"]
        message_id = msg["message_id"]
        text = f"<i>{escape_html(transcript.strip())}</i>"
        tg_api(
            token, "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_to_message_id=message_id,
            allow_sending_without_reply=True,
        )
        log.info(
            f"[{agent}] auto-transcribed voice in group {chat_id}"
        )
    except Exception:
        log.exception(
            f"[{agent}] auto-transcribe failed"
        )


def _push_group_message_to_jsonl(agent: str, cfg: dict, msg: dict) -> None:
    """Append group message to JSONL log file for Cognee pipeline.

    Fire-and-forget via _OV_POOL. PII sanitization handled by external script.
    Config key: 'group_log_jsonl_script' -- path to log-chat-message.py
    """
    try:
        script = cfg.get("group_log_jsonl_script")
        if not script:
            return
        script_path = Path(expand(script))
        if not script_path.exists():
            log.debug(f"[jsonl-log] script not found: {script_path}")
            return

        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(msg, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            log.warning(
                f"[jsonl-log] script failed: {result.stderr[:200]}"
            )
    except Exception:
        log.exception("[jsonl-log] failed to log group message")


def _load_group_chat_context(cfg: dict, chat_id: int) -> str:
    """Load last N messages from raw chat log for group context injection."""
    raw_dir = cfg.get("group_context_raw_dir", "")
    if not raw_dir:
        return ""
    max_lines = cfg.get("group_context_lines", 50)
    raw_path = Path(expand(raw_dir)) / f"{chat_id}.txt"
    if not raw_path.exists():
        return ""
    try:
        with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        tail = lines[-max_lines:] if len(lines) > max_lines else lines
        if not tail:
            return ""
        return "".join(tail).strip()
    except Exception as exc:
        log.debug(f"[group-ctx] raw log read failed: {exc}")
        return ""


def _search_cognee_context(cfg: dict, chat_id: int, query: str) -> str:
    """Search Cognee for semantic context relevant to the incoming message."""
    cognee_url = cfg.get("group_context_cognee_url", "")
    if not cognee_url:
        return ""
    datasets_map = cfg.get("group_context_cognee_datasets", {})
    dataset = datasets_map.get(str(chat_id), "")
    if not dataset:
        return ""
    # Truncate query to 200 chars for search
    q = (query or "").strip()[:200]
    if not q:
        return ""
    try:
        resp = requests.post(
            f"{cognee_url}/search",
            json={"query": q, "dataset": dataset, "top_k": 3},
            timeout=5,
        )
        if resp.status_code != 200:
            return ""
        data = resp.json()
        results = data.get("results", [])
        chunks = []
        for r in results:
            sr = r.get("search_result", [])
            if isinstance(sr, list):
                chunks.extend(str(s) for s in sr if s)
            elif sr:
                chunks.append(str(sr))
        if not chunks:
            return ""
        return "\n".join(chunks[:5])
    except Exception as exc:
        log.debug(f"[group-ctx] cognee search failed: {exc}")
        return ""


def _push_group_message_to_ov(agent: str, cfg: dict, msg: dict) -> None:
    """Push a group chat message to OpenViking for semantic logging.

    Fire-and-forget via _OV_POOL. Uses a separate OV user namespace
    (configured via 'group_log_ov_user' in agent config) so group
    messages don't mix with agent conversation memories.

    Two-track pipeline:
    1. RAW: every message saved as-is via temp_upload -> add_resource (immutable archive)
    2. EXTRACT: LLM extracts semantic memories from substantive messages
    """
    try:
        ov_url = cfg.get("openviking_url")
        if not ov_url:
            return
        # Prefer dedicated group key, fallback to agent key
        ov_key_file = cfg.get("group_log_ov_key_file") or cfg.get("openviking_key_file")
        if not ov_key_file:
            log.debug("[ov-group] no OV key file configured, skipping")
            return
        key_path = Path(expand(ov_key_file))
        if not key_path.exists():
            log.debug(f"[ov-group] key file not found: {key_path}")
            return
        key = key_path.read_text().strip()
        ov_account = cfg.get("openviking_account", "default")
        ov_user = cfg.get("group_log_ov_user", "")
        if not ov_user:
            return  # feature disabled

        headers = {
            "X-API-Key": key,
            "X-OpenViking-Account": ov_account,
            "X-OpenViking-User": ov_user,
            "Content-Type": "application/json",
        }
        headers_multipart = {
            "X-API-Key": key,
            "X-OpenViking-Account": ov_account,
            "X-OpenViking-User": ov_user,
        }
        base = f"{ov_url.rstrip('/')}/api/v1"

        # Format message content
        from_user = msg.get("from") or {}
        sender_name = (
            from_user.get("first_name", "")
            + (" " + from_user.get("last_name", "") if from_user.get("last_name") else "")
        ).strip() or "Unknown"
        username = from_user.get("username", "")
        text = (msg.get("text") or msg.get("caption") or "").strip()
        msg_date = msg.get("date", 0)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(msg_date))
        date_slug = time.strftime("%Y-%m-%d", time.gmtime(msg_date))

        # Build formatted content
        lines = [
            f"[EdgeLab Chat] {ts}",
            f"From: {sender_name}" + (f" (@{username})" if username else ""),
        ]
        if text:
            lines.append(text)

        # Detect links in entities
        entities = msg.get("entities") or msg.get("caption_entities") or []
        links = []
        raw_text = msg.get("text") or msg.get("caption") or ""
        for ent in entities:
            if ent.get("type") == "url":
                url = raw_text[ent["offset"]:ent["offset"] + ent["length"]]
                links.append(url)
            elif ent.get("type") == "text_link":
                links.append(ent.get("url", ""))
        if links:
            lines.append("Links: " + ", ".join(links))

        # Media type indicators
        media_types = []
        if msg.get("photo"):
            media_types.append("[Photo]")
        if msg.get("video"):
            media_types.append("[Video]")
        if msg.get("video_note"):
            media_types.append("[VideoNote]")
        if msg.get("animation"):
            media_types.append("[GIF]")
        if msg.get("voice") or msg.get("audio"):
            media_types.append("[Voice]")
        if msg.get("document"):
            doc = msg["document"]
            doc_name = doc.get("file_name", "unknown")
            mime = doc.get("mime_type", "")
            media_types.append(f"[Document: {doc_name} ({mime})]")
        if msg.get("sticker"):
            media_types.append("[Sticker]")
        if msg.get("poll"):
            media_types.append(f"[Poll: {msg['poll'].get('question', '')}]")
        if msg.get("contact"):
            media_types.append("[Contact]")
        if msg.get("location") or msg.get("venue"):
            media_types.append("[Location]")
        if media_types:
            lines.append(" ".join(media_types))

        # Forward context
        fwd_from = msg.get("forward_from") or msg.get("forward_from_chat")
        fwd_name = msg.get("forward_sender_name")
        if fwd_from or fwd_name:
            origin = (
                (fwd_from or {}).get("title")
                or (fwd_from or {}).get("first_name")
                or fwd_name
                or "unknown"
            )
            lines.append(f"Forwarded from: {origin}")

        # Reply context
        reply_msg = msg.get("reply_to_message")
        if reply_msg:
            quoted = (reply_msg.get("text") or reply_msg.get("caption") or "")[:100]
            if quoted:
                lines.append(f'Re: "{quoted}"')

        content = "\n".join(lines)

        # ---- TRACK 1: RAW store (every message, no filtering) ----
        try:
            msg_id = msg.get("message_id", int(time.time()))
            slug = f"msg-{date_slug}-{msg_id}"
            # Build frontmatter -- detect message type
            raw_type = "text"
            if msg.get("voice") or msg.get("audio"):
                raw_type = "voice"
            elif msg.get("video"):
                raw_type = "video"
            elif msg.get("video_note"):
                raw_type = "video_note"
            elif msg.get("animation"):
                raw_type = "animation"
            elif msg.get("photo"):
                raw_type = "photo"
            elif msg.get("document"):
                raw_type = "document"
            elif msg.get("sticker"):
                raw_type = "sticker"
            elif msg.get("poll"):
                raw_type = "poll"
            elif msg.get("contact"):
                raw_type = "contact"
            elif msg.get("location") or msg.get("venue"):
                raw_type = "location"
            if fwd_from or fwd_name:
                raw_type = f"forward:{raw_type}"

            # Sanitize frontmatter values (prevent YAML injection)
            def _sanitize_fm(val: str) -> str:
                return val.replace("\n", " ").replace("---", "").replace(":", " ").strip()[:100]

            chat_id = (msg.get("chat") or {}).get("id", 0)
            raw_content = (
                f"---\n"
                f"source: edgelab-chat\n"
                f"type: {raw_type}\n"
                f"sender: \"{_sanitize_fm(sender_name)}\"\n"
                f"username: \"{_sanitize_fm(username)}\"\n"
                f"date: {date_slug}\n"
                f"timestamp: {ts}\n"
                f"message_id: {msg_id}\n"
                f"chat_id: {chat_id}\n"
                f"compiled: false\n"
                f"---\n\n"
                f"{content}\n"
            )

            # Write raw file to temp, then store as resource, then fs/mv
            import tempfile as _tf
            with _tf.NamedTemporaryFile(
                mode="w", suffix=".md", prefix=f"raw-{slug}-", delete=False
            ) as tmp:
                tmp.write(raw_content)
                tmp_path = tmp.name

            try:
                with open(tmp_path, "rb") as fh:
                    up = requests.post(
                        f"{base}/resources/temp_upload",
                        headers=headers_multipart,
                        files={"file": (f"raw-{slug}.md", fh)},
                        data={"filename": f"raw-{slug}.md"},
                        timeout=15,
                    )
                if up.status_code == 200:
                    temp_file_id = up.json().get("result", {}).get("temp_file_id", "")
                    if temp_file_id:
                        add = requests.post(
                            f"{base}/resources",
                            headers=headers,
                            json={"temp_file_id": temp_file_id},
                            timeout=30,
                        )
                        if add.status_code == 200:
                            # Move from resources/ to user raw/ via fs/mv.
                            # OV holds a short-lived indexer lock on the just-added
                            # resource (observed 1-3s). Try once immediately, then
                            # back off only on retryable (5xx/429) errors. Bounded
                            # deadline protects the shared _OV_POOL (2 workers) so
                            # TRACK 2 always gets a chance to run after this block.
                            from_uri = add.json().get("result", {}).get("root_uri", "")
                            if not from_uri:
                                log.warning(
                                    f"[ov-group] raw add_resource 200 but no root_uri: "
                                    f"{slug} (file stuck in resources/)"
                                )
                            else:
                                target = f"viking://user/{ov_user}/raw/{slug}.md"
                                mv_ok = False
                                mv_last_status = 0
                                mv_last_body = ""
                                mkdir_tried = False
                                # Attempt schedule: try immediately, then backoff on
                                # retryable failures. Backoff caps total wall time at
                                # ~8s (deadline) to avoid pool saturation.
                                backoff = [1.5, 3.0, 4.0]  # seconds between retries
                                deadline = time.time() + 8.0
                                attempt = 0
                                while attempt <= len(backoff):
                                    attempt += 1
                                    try:
                                        mv = requests.post(
                                            f"{base}/fs/mv",
                                            headers=headers,
                                            json={"from_uri": from_uri, "to_uri": target},
                                            timeout=5,
                                        )
                                    except requests.RequestException as re:
                                        mv_last_status = -1
                                        mv_last_body = f"transport: {type(re).__name__}: {re}"[:200]
                                        # transport errors are retryable
                                    else:
                                        mv_last_status = mv.status_code
                                        mv_last_body = (mv.text or "")[:200]
                                        if mv.status_code == 200:
                                            log.info(
                                                f"[ov-group] raw saved: {slug} from "
                                                f"{sender_name} (attempt {attempt})"
                                            )
                                            mv_ok = True
                                            break
                                        # Auto-create target dir on missing-directory (once).
                                        # If mkdir succeeds, allow one more retry of mv
                                        # even though the original mv was a 4xx (the dir
                                        # now exists, so the next attempt is meaningful).
                                        just_fixed_dir = False
                                        if (not mkdir_tried
                                                and "no such directory" in mv_last_body.lower()):
                                            mkdir_tried = True
                                            try:
                                                mk = requests.post(
                                                    f"{base}/fs/mkdir",
                                                    headers=headers,
                                                    json={"uri": f"viking://user/{ov_user}/raw/"},
                                                    timeout=5,
                                                )
                                                log.info(
                                                    f"[ov-group] raw/ mkdir status="
                                                    f"{mk.status_code} for {ov_user}"
                                                )
                                                if mk.status_code == 200:
                                                    just_fixed_dir = True
                                            except requests.RequestException as mre:
                                                log.warning(f"[ov-group] raw/ mkdir error: {mre}")
                                        # Retry on 5xx / 429 / transport, or immediately
                                        # after a successful mkdir recovery. Break on 4xx.
                                        if not just_fixed_dir and not (
                                                mv.status_code >= 500 or mv.status_code == 429):
                                            break
                                    # Stop if out of budget or no more delays left
                                    if attempt > len(backoff) or time.time() >= deadline:
                                        break
                                    delay = backoff[attempt - 1]
                                    # small jitter to avoid thundering herd on lock
                                    delay += _random.uniform(0, 0.3 * delay)
                                    # never sleep past deadline
                                    delay = min(delay, max(0.0, deadline - time.time()))
                                    if delay <= 0:
                                        break
                                    time.sleep(delay)
                                if not mv_ok:
                                    log.warning(
                                        f"[ov-group] raw fs/mv failed after {attempt} attempts: "
                                        f"status={mv_last_status} file={from_uri} body={mv_last_body}"
                                    )
                        else:
                            log.warning(f"[ov-group] raw add_resource failed: {add.status_code}")
                else:
                    log.warning(f"[ov-group] raw temp_upload failed: {up.status_code}")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as e:
            log.warning(f"[ov-group] raw store failed: {e}")

        # ---- TRACK 2: EXTRACT (LLM semantic memories) ----
        sid = None
        r = requests.post(f"{base}/sessions", headers=headers, json={}, timeout=10)
        if r.status_code != 200:
            log.warning(f"[ov-group] create session failed: {r.status_code}")
            return
        sid = r.json().get("result", {}).get("session_id")
        if not sid:
            return
        try:
            requests.post(
                f"{base}/sessions/{sid}/messages",
                headers=headers,
                json={"role": "user", "content": content[:3000]},
                timeout=10,
            )
            ext = requests.post(
                f"{base}/sessions/{sid}/extract",
                headers=headers, json={}, timeout=60,
            )
            extracted = ext.json().get("result", []) if ext.status_code == 200 else []
            log.info(
                f"[ov-group] extracted {len(extracted)} memories "
                f"from {sender_name} in chat {msg['chat']['id']}"
            )
        finally:
            try:
                requests.delete(f"{base}/sessions/{sid}", headers=headers, timeout=5)
            except Exception:
                pass
    except Exception as e:
        log.warning(f"[ov-group] push failed for agent={agent}: {e}")


# ---------------------------------------------------------------------------
# Heartbeat (no-op / log-only, no external dependencies)
# ---------------------------------------------------------------------------

def record_heartbeat(
    agent: str, started_at_ms: int, dur_ms: int, status: str, chat_id: int
) -> None:
    """Log heartbeat info. Override this function to push to your analytics backend."""
    log.info(
        f"[heartbeat] agent={agent} chat={chat_id} status={status} "
        f"duration={dur_ms}ms started={started_at_ms}"
    )


# ---------------------------------------------------------------------------
# Main message processing
# ---------------------------------------------------------------------------

def process_update(agent: str, cfg: dict, token: str, update: dict, allowlist: list[int]) -> None:
    """Handle one Telegram update. Ignore non-message / non-allowlisted / non-addressed."""
    is_webhook = update.get("_webhook", False)
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    # Group/supergroup gating: check chat_id against allowlist_group_ids
    chat_type = (msg.get("chat") or {}).get("type", "private")
    is_group = chat_type in ("group", "supergroup")
    if not is_webhook and is_group:
        chat_id_check = msg["chat"]["id"]
        allowlist_groups = cfg.get("_allowlist_group_ids", [])
        if chat_id_check not in allowlist_groups:
            log.info(
                f"[{agent}] denied group chat_id={chat_id_check}"
            )
            return

    user_id = (msg.get("from") or {}).get("id")
    if not is_webhook and user_id not in allowlist:
        # group_allow_all: bypass user allowlist in group chats for this agent
        if not (is_group and cfg.get("group_allow_all")):
            log.info(f"denied user_id={user_id} agent={agent}")
            return

    # Early voice transcription for group addressing check
    # Without this, voice messages in groups are always skipped (no text to match agent name)
    bot_username = cfg.get("_bot_username")
    if is_group and not msg.get("_voice_transcript"):
        media_ref_early = resolve_media_ref(msg)
        if media_ref_early and media_ref_early["type"] in ("voice", "audio", "video_note"):
            early_local = download_telegram_file(token, media_ref_early["file_id"], "voice", None)
            if early_local:
                early_transcript = transcribe_audio(early_local, agent_cfg=cfg) or ""
                if early_transcript:
                    msg["_voice_transcript"] = early_transcript
                    log.info(f"[{agent}] early voice transcription done ({len(early_transcript)} chars)")

    # Group-chat gating: only respond if addressed via @mention, name, or reply
    if not is_webhook and not is_addressed_to_agent(agent, msg, bot_username, cfg):
        chat_type = (msg.get("chat") or {}).get("type", "?")
        log.info(f"[{agent}] group chat {chat_type}, not addressed, skip")
        return
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or msg.get("caption") or "").strip()
    message_id = msg.get("message_id")

    # Handle gateway commands (/status, /reset, /help, /new) -- don't go to claude
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        if handle_command(token, chat_id, agent, cmd, args, cfg):
            log.info(f"[{agent}] command: {cmd} {args}".strip())
            return

    # Classify source for memory extraction provenance
    source_tag, source_label = classify_source(msg)

    # Handle media attachments
    media_note = ""
    media_ref = resolve_media_ref(msg)
    if media_ref:
        send_chat_action(token, chat_id, "typing")
        local = download_telegram_file(token, media_ref["file_id"], media_ref["type"], media_ref["file_name"])
        if local:
            mtype = media_ref["type"]
            if mtype in ("voice", "audio", "video_note"):
                # Use pre-transcribed text from producer if available
                transcript = msg.get("_voice_transcript") or ""
                if not transcript:
                    transcript = transcribe_audio(local, agent_cfg=cfg) or ""
                if transcript:
                    media_note = f"\n\n[Voice/audio transcript]: {transcript}"
                else:
                    media_note = f"\n\n[Audio transcription failed: {local}]"
            elif mtype == "video":
                # Video: attach path, claude Read tool can't play video but can reference
                media_note = f"\n\n[Video: {local} ({media_ref.get('mime_type') or 'video'})]"
            elif mtype == "photo":
                media_note = f"\n\n[Image: {local}] -- read via Read tool"
            elif mtype == "document":
                fname = media_ref.get("file_name") or local.name
                media_note = f"\n\n[File {fname}: {local}] -- read via Read tool (for PDF use pypdf or shell pdftotext)"
            elif mtype == "sticker":
                sticker_obj = msg.get("sticker") or {}
                sticker_emoji = sticker_obj.get("emoji", "")
                sticker_set = sticker_obj.get("set_name", "")
                sticker_uid = sticker_obj.get("file_unique_id", "")
                desc = _get_sticker_description(sticker_uid, sticker_emoji, sticker_set, local)
                media_note = f"\n\n[Sticker: {desc}]"
        else:
            media_note = f"\n\n[Failed to download {media_ref['type']} (possibly >20MB)]"

    if not text and not media_note:
        return  # nothing to process
    if not text:
        text = "(user sent attachment)"
    text = text + media_note

    # Ack reaction: eyes emoji to show message is being processed
    if message_id:
        set_reaction(token, chat_id, message_id, "\U0001f440")

    # Prepend source tag for OV memory extraction (invisible to agent context, used by gateway OV push)
    text_for_agent = text  # what agent sees
    # Forward context: agent sees who forwarded the message
    if source_tag == "forwarded":
        fwd_name = source_label.replace("forwarded from: ", "")
        text_for_agent = f"[Forwarded from: {fwd_name}]\n{text}"

    # Reply context (openclaw pattern: untrusted metadata block)
    # When user replies to a message, include its content so agent knows the reference.
    reply_msg = msg.get("reply_to_message")
    if isinstance(reply_msg, dict):
        reply_body = str(reply_msg.get("text") or reply_msg.get("caption") or "")
        reply_doc = reply_msg.get("document") or {}
        if isinstance(reply_doc, dict) and reply_doc and not reply_body:
            reply_body = f"[file: {reply_doc.get('file_name', '?')}]"
        # Fallback for media-only replies (photo/sticker/voice/video)
        if not reply_body:
            if reply_msg.get("photo"):
                reply_body = "[photo]"
            elif reply_msg.get("sticker"):
                reply_body = "[sticker]"
            elif reply_msg.get("voice"):
                reply_body = "[voice]"
            elif reply_msg.get("video") or reply_msg.get("video_note"):
                reply_body = "[video]"
            elif reply_msg.get("audio"):
                reply_body = "[audio]"
        reply_from = reply_msg.get("from") or {}
        # Only label as agent's own message when reply is from THIS bot (compare user ids).
        # Generic is_bot=True would let users spoof agent output via replies to other bots.
        my_bot_id = cfg.get("_bot_user_id")
        is_self_reply = (
            isinstance(reply_from, dict)
            and my_bot_id is not None
            and reply_from.get("id") == my_bot_id
        )
        if is_self_reply:
            sender_label = "agent's previous message"
        elif isinstance(reply_from, dict) and reply_from.get("is_bot"):
            # Another bot's message — label explicitly so agent does not trust it as own output.
            sender_label = "other bot"
        else:
            sender_label = (
                reply_from.get("first_name") if isinstance(reply_from, dict) else None
            ) or "unknown"
            if isinstance(reply_from, dict):
                reply_uname = reply_from.get("username")
                reply_uid = reply_from.get("id")
                if reply_uname:
                    sender_label = f"{sender_label} (@{reply_uname})"
                if reply_uid:
                    sender_label = f"{sender_label} [id:{reply_uid}]"
        if reply_body:
            truncated = len(reply_body) > 1200
            snippet = reply_body[:1200].replace("\x00", "")
            payload = {"sender": sender_label, "body": snippet}
            if truncated:
                payload["truncated"] = True
            reply_block = (
                "[Replied message (untrusted metadata, for context only):]\n"
                + json.dumps(payload, ensure_ascii=False)
                + "\n"
            )
            text_for_agent = reply_block + text_for_agent

    text_for_ov = f"[source:{source_tag} | {source_label}]\n{text}"

    # -----------------------------------------------------------------------
    # Group vs Private: choose streaming mode and system reminder per context
    # -----------------------------------------------------------------------
    chat_type = (msg.get("chat") or {}).get("type", "private")
    is_group = chat_type in ("group", "supergroup")

    if is_group:
        streaming_mode = cfg.get(
            "streaming_mode_group",
            cfg.get("streaming_mode", "off"),
        )
    else:
        streaming_mode = cfg.get(
            "streaming_mode_private",
            cfg.get("streaming_mode", "partial"),
        )

    _DEFAULT_GROUP_REMINDER = (
        "You are in a PUBLIC group chat. Rules:\n"
        "1. Answer concisely -- result only, no process\n"
        "2. Do NOT show: commands, file paths, logs, intermediate steps\n"
        "3. Do NOT reveal: private data, API keys, internal architecture\n"
        "4. Keep response under 500 characters unless asked for detail\n"
        "5. No code blocks unless specifically requested"
    )
    if is_group:
        active_reminder = cfg.get("system_reminder_group", "")
        if not active_reminder:
            active_reminder = _DEFAULT_GROUP_REMINDER
    else:
        active_reminder = cfg.get(
            "system_reminder_private",
            cfg.get("system_reminder", ""),
        )

    # Inject group chat context (raw history + Cognee semantic) into system prompt
    if is_group:
        raw_ctx = _load_group_chat_context(cfg, chat_id)
        if raw_ctx:
            ctx_lines = cfg.get("group_context_lines", 50)
            active_reminder += (
                f"\n\n--- Recent chat messages (last {ctx_lines}) ---\n"
                f"{raw_ctx}\n--- End of chat history ---"
            )
        cognee_ctx = _search_cognee_context(cfg, chat_id, text)
        if cognee_ctx:
            active_reminder += (
                "\n\n--- Relevant knowledge from chat history (Cognee) ---\n"
                f"{cognee_ctx}\n--- End of Cognee context ---"
            )

    # Group context: prepend chat title and sender name so agent knows the source
    if is_group:
        chat_title = (msg.get("chat") or {}).get("title", "unknown")
        from_user = msg.get("from") or {}
        sender = from_user.get("first_name", "unknown")
        username = from_user.get("username")
        from_user_id = from_user.get("id")
        sender_label = f"{sender} (@{username})" if username else sender
        if from_user_id:
            sender_label = f"{sender_label} [id:{from_user_id}]"
        text_for_agent = (
            f"[Group: {chat_title} | From: {sender_label}]\n{text_for_agent}"
        )

    log.info(f"[{agent}] chat={chat_id} user={user_id} src={source_tag}: {text[:100]}")

    started_ms = int(time.time() * 1000)
    send_chat_action(token, chat_id, "typing")

    # No placeholder; status message created lazily on first real task-boundary event.
    status_msg_id = [None]
    last_edit_t = [0.0]
    last_sent = [""]

    def status_update(text_html: str) -> None:
        text_html = text_html[:3900]
        now = time.time()
        if text_html == last_sent[0] or now - last_edit_t[0] < 2.0:
            return
        last_edit_t[0] = now
        last_sent[0] = text_html
        if status_msg_id[0] is None:
            # Lazy create status message on first real event (TodoWrite or Agent dispatch)
            try:
                r = tg_api(token, "sendMessage", chat_id=chat_id, text=text_html, parse_mode="HTML")
                status_msg_id[0] = r.get("result", {}).get("message_id")
            except Exception:
                pass
        else:
            edit_message(token, chat_id, status_msg_id[0], text_html, html=True)

    invoke_cfg = {
        **cfg,
        "streaming_mode": streaming_mode,
        "_active_system_reminder": active_reminder,
        "_typing_refresh_cb": lambda: send_chat_action(token, chat_id, "typing"),
        "_status_update_cb": status_update,
    }
    response, dur_ms, status_int, written_files = invoke_claude(
        agent, invoke_cfg, chat_id, text_for_agent,
    )

    # Delete status message before sending final reply (keep it clean)
    if status_msg_id[0]:
        delete_message(token, chat_id, status_msg_id[0])

    if not response:
        response = "agent did not respond"
    status = "completed" if status_int else "error"

    record_heartbeat(agent, started_ms, dur_ms, status, chat_id)

    # Append to hot memory (always, regardless of source)
    append_to_hot_memory(agent, cfg, text_for_agent, response or "(inline)", source_tag)

    # Skip OV push if voice transcription failed (would pollute with error text)
    transcribe_failed = media_note and "transcription failed" in media_note

    # OV push via bounded thread pool -- only for own content or forwarded (marked)
    if source_tag in ("own_text", "own_voice", "forwarded") and not transcribe_failed:
        _OV_POOL.submit(
            push_to_openviking, agent, cfg, text_for_ov,
            response or "(answered inline)", chat_id
        )
    # external_media -> hot only, not OV memory extraction (to avoid polluting preferences)

    # Parse [REACT:emoji] markers from agent response -- set reaction on user message
    if response and message_id:
        for _react_match in _re.finditer(r"\[REACT:([^\]]+)\]", response):
            _react_emoji = _react_match.group(1).strip()
            set_reaction(token, chat_id, message_id, _react_emoji)
        response = _re.sub(r"\s*\[REACT:[^\]]+\]\s*", "", response).strip()

    if response:  # not already delivered via edit-in-place
        try:
            send_message(token, chat_id, response, reply_to=message_id)
            log.info(f"[{agent}] replied chat={chat_id} dur={dur_ms}ms")
        except Exception as e:
            log.exception(f"reply failed: {e}")

    # Send written files as documents (sendDocument)
    if written_files:
        workspace = Path(expand(cfg["workspace"])).resolve()
        for fpath in written_files:
            try:
                # Resolve relative paths against agent workspace, not gateway CWD
                raw = Path(fpath)
                p = (workspace / raw).resolve() if not raw.is_absolute() else raw.resolve()
                # Security: only send files within agent workspace
                if not p.is_relative_to(workspace):
                    log.warning(
                        f"[{agent}] send_document blocked:"
                        f" {fpath} outside workspace"
                    )
                    continue
                if p.exists() and p.stat().st_size > 0:
                    send_chat_action(token, chat_id, "upload_document")
                    send_document(
                        token, chat_id, str(p),
                        caption=f"<code>{escape_html(p.name)}</code>",
                    )
                    log.info(
                        f"[{agent}] sent document:"
                        f" {p.name} chat={chat_id}"
                    )
            except Exception as e:
                log.warning(
                    f"[{agent}] send_document failed"
                    f" for {fpath}: {e}"
                )


# ---------------------------------------------------------------------------
# Bot commands menu
# ---------------------------------------------------------------------------

_BOT_COMMANDS = [
    {"command": "new", "description": "Новая сессия (полный handoff)"},
    {"command": "status", "description": "Статус сессии и памяти"},
    {"command": "stop", "description": "Остановить текущую задачу"},
    {"command": "compact", "description": "Компактизация памяти"},
    {"command": "reset", "description": "Сброс без handoff (force)"},
    {"command": "help", "description": "Справка по командам"},
]


# ---------------------------------------------------------------------------
# Polling: producer-consumer architecture
# ---------------------------------------------------------------------------

def _is_oob_command(text: str) -> bool:
    """Check if message text is an out-of-band command for instant handling."""
    if not text or not text.startswith("/"):
        return False
    parts = text.split(None, 1)
    cmd = parts[0].lower()
    # Strip @botname suffix (e.g. /stop@mybotname)
    if "@" in cmd:
        cmd = cmd.split("@")[0]
    return cmd in _OOB_COMMANDS


def _handle_oob_command(
    agent: str, token: str, chat_id: int, text: str,
    cfg: dict | None = None,
) -> None:
    """Handle out-of-band command immediately from producer thread.

    Handles: /stop, /status, /reset force
    Non-force /reset and other commands are queued for consumer.
    """
    parts = text.split(None, 2)
    cmd = parts[0].lower()
    # Strip @botname suffix
    if "@" in cmd:
        cmd = cmd.split("@")[0]
    args = parts[1] if len(parts) > 1 else ""

    if cmd in ("/stop", "/cancel"):
        with _ACTIVE_PROCS_LOCK:
            proc = _ACTIVE_PROCS.get((agent, chat_id))
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
                reply = (
                    "<b>stopped</b>\n\n"
                    "<i>agent interrupted current task</i>"
                )
            except Exception as e:
                reply = (
                    f"<b>stop error</b>: "
                    f"{escape_html(str(e)[:100])}"
                )
        else:
            reply = "<b>nothing to stop</b> -- agent is idle"
        try:
            tg_api(
                token, "sendMessage",
                chat_id=chat_id, text=reply, parse_mode="HTML",
            )
        except Exception:
            pass
        log.info(f"[{agent}] OOB /stop chat={chat_id}")
        return

    if cmd == "/status":
        handle_command(token, chat_id, agent, "/status", "", cfg=cfg or {})
        log.info(f"[{agent}] OOB /status chat={chat_id}")
        return

    if cmd == "/reset" and args.strip().lower() == "force":
        # Kill active subprocess if any
        with _ACTIVE_PROCS_LOCK:
            proc = _ACTIVE_PROCS.pop((agent, chat_id), None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
        # Delete session files
        sid_file = STATE_DIR / f"sid-{agent}-{chat_id}.txt"
        first_file = STATE_DIR / f"sid-{agent}-{chat_id}.first"
        old_sid = ""
        if sid_file.exists():
            old_sid = sid_file.read_text().strip()
        sid_file.unlink(missing_ok=True)
        first_file.unlink(missing_ok=True)
        reply = (
            "<b>session reset (force)</b>\n\n"
            f"old: <code>{escape_html(old_sid[:8])}...</code>\n"
            "next message = new session"
        )
        try:
            tg_api(
                token, "sendMessage",
                chat_id=chat_id, text=reply, parse_mode="HTML",
            )
        except Exception:
            pass
        log.info(f"[{agent}] OOB /reset force chat={chat_id}")
        return


def _init_bot_metadata(agent: str, cfg: dict, token: str) -> None:
    """Cache bot_username and register commands menu (once per agent)."""
    if cfg.get("_bot_username"):
        return
    try:
        info = tg_api(token, "getMe")
        result = info.get("result") or {}
        bot_username = result.get("username")
        cfg["_bot_username"] = bot_username
        cfg["_bot_user_id"] = result.get("id")
        try:
            tg_api(token, "setMyCommands", commands=_BOT_COMMANDS)
        except Exception as e:
            log.warning(f"[{agent}] setMyCommands failed: {e}")
    except Exception:
        pass


def polling_producer(
    agent: str, cfg: dict, allowlist: list[int], offset_file: Path
) -> None:
    """Daemon thread: polls Telegram, routes OOB commands immediately,
    queues regular messages for consumer.

    OOB commands (/stop, /status, /reset force) are handled instantly
    even when the consumer thread is blocked on invoke_claude().
    """
    token = _resolve_telegram_token(cfg)
    _init_bot_metadata(agent, cfg, token)
    msg_queue = _MSG_QUEUES[agent]
    poll_interval_sec = 1  # producer polls every 1s for responsiveness

    log.info(f"[{agent}] producer thread started")

    while not _SHUTDOWN_EVENT.is_set():
        # Read offset
        offset = 0
        if offset_file.exists():
            try:
                offset = int(offset_file.read_text().strip() or "0")
            except Exception:
                offset = 0

        try:
            r = tg_api(
                token, "getUpdates",
                offset=offset, timeout=0, limit=10,
            )
        except Exception as e:
            log.warning(f"[{agent}] producer getUpdates failed: {e}")
            time.sleep(poll_interval_sec)
            continue

        updates = r.get("result", [])
        for upd in updates:
            new_offset = upd["update_id"] + 1
            offset_file.write_text(str(new_offset))

            # Handle callback queries (inline button presses)
            cq = upd.get("callback_query")
            if cq:
                dispatch_callback_query(token, agent, cfg, cq)
                continue

            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue

            # Group/supergroup gating: check chat_id against allowlist_group_ids
            chat_type = (msg.get("chat") or {}).get("type", "private")
            is_group = chat_type in ("group", "supergroup")
            if is_group:
                group_chat_id = msg["chat"]["id"]
                allowlist_groups = cfg.get("_allowlist_group_ids", [])
                if group_chat_id not in allowlist_groups:
                    log.info(
                        f"[{agent}] producer denied group "
                        f"chat_id={group_chat_id}"
                    )
                    continue

            # Log ALL messages from allowlisted groups to OpenViking
            # (fire-and-forget, before user_id check -- logs even
            # non-allowlisted users' messages for group context)
            if is_group and cfg.get("group_log_ov_user"):
                _OV_POOL.submit(
                    _push_group_message_to_ov, agent, cfg, msg
                )
            # JSONL logging for Cognee pipeline (parallel to OV)
            if is_group and cfg.get("group_log_jsonl_script"):
                _OV_POOL.submit(
                    _push_group_message_to_jsonl, agent, cfg, msg
                )

            user_id = (msg.get("from") or {}).get("id")
            if user_id not in allowlist:
                # group_allow_all: bypass user allowlist in group chats
                if not (is_group and cfg.get("group_allow_all")):
                    log.info(
                        f"[{agent}] producer denied user_id={user_id}"
                    )
                    continue

            # Per-topic routing: if agent has topic_routing config, only accept
            # messages from specified topics in specified groups
            topic_routing = cfg.get("topic_routing")
            if topic_routing:
                chat_id_str = str(msg["chat"]["id"])
                thread_id = msg.get("message_thread_id")
                if chat_id_str in topic_routing:
                    allowed_topics = topic_routing[chat_id_str]
                    if thread_id is None or str(thread_id) not in allowed_topics:
                        continue  # message not in routed topic for this agent

            # Early voice transcription for group addressing check
            bot_username = cfg.get("_bot_username")
            if is_group and not msg.get("_voice_transcript"):
                media_ref_early = resolve_media_ref(msg)
                if media_ref_early and media_ref_early["type"] in ("voice", "audio", "video_note"):
                    early_local = download_telegram_file(token, media_ref_early["file_id"], "voice", None)
                    if early_local:
                        early_transcript = transcribe_audio(early_local, agent_cfg=cfg) or ""
                        if early_transcript:
                            msg["_voice_transcript"] = early_transcript
                            log.info(f"[{agent}] producer early transcription ({len(early_transcript)} chars)")

            # Group-chat gating
            if not is_addressed_to_agent(agent, msg, bot_username, cfg):
                continue

            chat_id = msg["chat"]["id"]
            text = (
                msg.get("text") or msg.get("caption") or ""
            ).strip()

            # Out-of-band commands: handle immediately in producer
            if _is_oob_command(text):
                # /reset without 'force' goes to consumer (it needs
                # blocking Claude save). Only /reset force is OOB.
                parts = text.split(None, 2)
                cmd = parts[0].lower()
                if "@" in cmd:
                    cmd = cmd.split("@")[0]
                args = parts[1].lower() if len(parts) > 1 else ""

                if cmd == "/new" or (cmd == "/reset" and args != "force"):
                    # /new and non-force /reset -> queue for consumer (blocking handoff)
                    msg_queue.put(upd)
                    continue

                try:
                    _handle_oob_command(agent, token, chat_id, text, cfg=cfg)
                except Exception:
                    log.exception(
                        f"[{agent}] OOB command failed: {text}"
                    )
                continue

            # Regular message -> queue for consumer
            msg_queue.put(upd)

        time.sleep(poll_interval_sec)

    log.info(f"[{agent}] producer thread stopped")


def _chat_worker(
    agent: str, cfg: dict, token: str, allowlist: list[int], chat_id: int
) -> None:
    """Per-chat worker thread: processes messages for a single chat_id sequentially.

    Exits when queue is empty for 60s (idle timeout) to avoid thread leak.
    """
    chat_queue = _CHAT_QUEUES[agent][chat_id]
    log.info(f"[{agent}] chat worker started for chat_id={chat_id}")

    idle_timeout = 60  # seconds to wait before exiting idle worker

    while not _SHUTDOWN_EVENT.is_set():
        try:
            upd = chat_queue.get(timeout=idle_timeout)
        except queue.Empty:
            # No messages for this chat -- exit worker, will be recreated on demand
            break

        try:
            process_update(agent, cfg, token, upd, allowlist)
        except Exception:
            log.exception(f"[{agent}] chat worker chat_id={chat_id} processing failed")
        finally:
            chat_queue.task_done()

    # Cleanup: remove worker reference, respawn if messages arrived during exit
    with _CHAT_LOCKS[agent]:
        _CHAT_WORKERS[agent].pop(chat_id, None)
        if not chat_queue.empty():
            # Messages arrived between timeout and cleanup -- spawn replacement
            t = threading.Thread(
                target=_chat_worker,
                args=(agent, cfg, token, allowlist, chat_id),
                name=f"chat-worker-{agent}-{chat_id}",
                daemon=True,
            )
            t.start()
            _CHAT_WORKERS[agent][chat_id] = t
            log.info(f"[{agent}] respawned worker for chat_id={chat_id} (messages pending)")
        else:
            _CHAT_QUEUES[agent].pop(chat_id, None)

    log.info(f"[{agent}] chat worker stopped for chat_id={chat_id}")


def message_consumer(
    agent: str, cfg: dict, token: str, allowlist: list[int]
) -> None:
    """Daemon thread: dispatches messages to per-chat worker threads.

    Each chat_id gets its own worker thread for parallel processing.
    Messages within the same chat are processed sequentially (ordered).
    Different chats are processed in parallel.
    """
    msg_queue = _MSG_QUEUES[agent]
    log.info(f"[{agent}] consumer dispatcher started (per-chat parallel mode)")

    while not _SHUTDOWN_EVENT.is_set():
        try:
            upd = msg_queue.get(timeout=2)
        except queue.Empty:
            continue

        try:
            # Extract chat_id from update
            msg = upd.get("message") or upd.get("channel_post") or {}
            chat_id = (msg.get("chat") or {}).get("id")
            if not chat_id:
                # Fallback: process in-place if no chat_id
                process_update(agent, cfg, token, upd, allowlist)
                continue

            # Route to per-chat queue, spawn worker if needed
            with _CHAT_LOCKS[agent]:
                if chat_id not in _CHAT_QUEUES[agent]:
                    _CHAT_QUEUES[agent][chat_id] = queue.Queue()

                _CHAT_QUEUES[agent][chat_id].put(upd)

                # Spawn worker thread if not running
                if chat_id not in _CHAT_WORKERS[agent] or not _CHAT_WORKERS[agent][chat_id].is_alive():
                    t = threading.Thread(
                        target=_chat_worker,
                        args=(agent, cfg, token, allowlist, chat_id),
                        name=f"chat-worker-{agent}-{chat_id}",
                        daemon=True,
                    )
                    t.start()
                    _CHAT_WORKERS[agent][chat_id] = t

        except Exception:
            log.exception(f"[{agent}] consumer dispatcher failed")
        finally:
            msg_queue.task_done()

    log.info(f"[{agent}] consumer dispatcher stopped")


# ---------------------------------------------------------------------------
# Webhook API -- lightweight HTTP server for external triggers
# ---------------------------------------------------------------------------

from http.server import HTTPServer, BaseHTTPRequestHandler as _BaseHandler


class _WebhookHandler(_BaseHandler):
    """Handle POST /hooks/agent -- inject message into agent queue."""

    # Set by main() before server starts
    gateway_cfg: dict = {}
    gateway_agents: dict = {}
    webhook_token: str = ""

    def log_message(self, fmt: str, *args: Any) -> None:
        log.debug(f"[webhook] {fmt % args}")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/hooks/agent":
            self._reply(404, {"error": "not found"})
            return

        # Auth check
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {self.webhook_token}" if self.webhook_token else ""
        if self.webhook_token and auth != expected:
            self._reply(401, {"error": "unauthorized"})
            return

        # Parse body
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            self._reply(400, {"error": "invalid json"})
            return

        agent_id = body.get("agentId", "")
        message = body.get("message", "")
        if not agent_id or not message:
            self._reply(400, {"error": "agentId and message required"})
            return

        if agent_id not in self.gateway_agents:
            self._reply(404, {"error": f"agent '{agent_id}' not found"})
            return

        # Inject into agent queue as synthetic update
        q = _MSG_QUEUES.get(agent_id)
        if not q:
            self._reply(503, {"error": f"agent '{agent_id}' queue not ready"})
            return

        # Build a synthetic Telegram-like update
        chat_id = body.get("chatId") or body.get("to")
        synthetic_msg = {
            "message_id": 0,
            "from": {"id": 0, "first_name": "webhook", "is_bot": False},
            "chat": {"id": int(chat_id) if chat_id else 0, "type": "private"},
            "date": int(time.time()),
            "text": message,
        }
        q.put({"update_id": 0, "message": synthetic_msg, "_webhook": True})
        log.info(f"[webhook] injected message for {agent_id}: {message[:80]}")
        self._reply(200, {"ok": True, "agent": agent_id})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            agents_status = {
                a: "online" for a in self.gateway_agents
            }
            self._reply(200, {"status": "ok", "agents": agents_status})
        else:
            self._reply(404, {"error": "not found"})

    def _reply(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _start_webhook_server(
    cfg: dict, agents: dict, port: int, token: str
) -> None:
    """Start webhook HTTP server in daemon thread."""
    _WebhookHandler.gateway_cfg = cfg
    _WebhookHandler.gateway_agents = agents
    _WebhookHandler.webhook_token = token

    server = HTTPServer(("127.0.0.1", port), _WebhookHandler)
    t = threading.Thread(
        target=server.serve_forever,
        name="webhook-server",
        daemon=True,
    )
    t.start()
    log.info(f"[webhook] HTTP server on 127.0.0.1:{port}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not CONFIG_PATH.exists():
        log.error(f"config not found: {CONFIG_PATH}")
        log.error("create config.json in the working directory (see docstring for format)")
        sys.exit(1)

    cfg = json.loads(CONFIG_PATH.read_text())
    allowlist = cfg.get("allowlist_user_ids", [])
    allowlist_groups = cfg.get("allowlist_group_ids", [])
    agents = {
        k: v for k, v in cfg["agents"].items() if v.get("enabled")
    }

    if not agents:
        log.error("no enabled agents in config")
        sys.exit(1)

    log.info(
        f"gateway started (producer-consumer), "
        f"agents={list(agents.keys())}, allowlist={allowlist}, "
        f"allowlist_groups={allowlist_groups}"
    )

    # Start webhook API server (optional)
    webhook_port = cfg.get("webhook_port", 0)
    if webhook_port:
        webhook_token = cfg.get("webhook_token", "")
        _start_webhook_server(cfg, agents, webhook_port, webhook_token)

    offsets = {a: STATE_DIR / f"offset-{a}.txt" for a in agents}
    threads: list[threading.Thread] = []

    for agent, acfg in agents.items():
        # Inject group allowlist into per-agent config for access in handlers
        acfg["_allowlist_group_ids"] = allowlist_groups

        # Initialize per-agent message queue and per-chat structures
        _MSG_QUEUES[agent] = queue.Queue()
        _CHAT_QUEUES[agent] = {}
        _CHAT_WORKERS[agent] = {}
        _CHAT_LOCKS[agent] = threading.Lock()

        # Read token for consumer thread
        token = _resolve_telegram_token(acfg)

        # Producer thread: polls Telegram, handles OOB commands
        t_prod = threading.Thread(
            target=polling_producer,
            args=(agent, acfg, allowlist, offsets[agent]),
            name=f"producer-{agent}",
            daemon=True,
        )
        t_prod.start()
        threads.append(t_prod)

        # Consumer thread: processes queued messages
        t_cons = threading.Thread(
            target=message_consumer,
            args=(agent, acfg, token, allowlist),
            name=f"consumer-{agent}",
            daemon=True,
        )
        t_cons.start()
        threads.append(t_cons)

    # Main thread waits for shutdown signal
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("gateway shutting down...")
        _SHUTDOWN_EVENT.set()
        for t in threads:
            t.join(timeout=5)
        log.info("gateway stopped")


if __name__ == "__main__":
    main()
