"""Read Claude Code JSONL usage files and identify the current 5-hour window."""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SESSION_DURATION = timedelta(hours=5)
DATA_PATH = Path("~/.claude/projects").expanduser()

logger = logging.getLogger(__name__)


def _parse_timestamp(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _model_display(raw: str) -> str:
    """Convert raw model ID to a short readable name."""
    s = raw.lower()
    if "opus" in s:
        # claude-opus-4-7 -> Opus 4.7, claude-opus-4-6 -> Opus 4.6
        import re
        m = re.search(r"opus-(\d+)-(\d+)", s)
        if m:
            return f"Opus {m.group(1)}.{m.group(2)}"
        return "Opus"
    if "sonnet" in s:
        import re
        m = re.search(r"sonnet-(\d+)-(\d+)", s)
        if m:
            return f"Sonnet {m.group(1)}.{m.group(2)}"
        return "Sonnet"
    if "haiku" in s:
        import re
        m = re.search(r"haiku-(\d+)-(\d+)", s)
        if m:
            return f"Haiku {m.group(1)}.{m.group(2)}"
        return "Haiku"
    return raw


def _load_all_entries(data_path: Path) -> List[Dict[str, Any]]:
    entries = []
    for jsonl_file in sorted(data_path.rglob("*.jsonl")):
        try:
            with open(jsonl_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if d.get("type") != "assistant":
                        continue
                    msg = d.get("message") or {}
                    usage = msg.get("usage")
                    if not usage:
                        continue
                    ts = _parse_timestamp(d.get("timestamp", ""))
                    if not ts:
                        continue

                    entries.append(
                        {
                            "timestamp": ts,
                            "model": msg.get("model") or d.get("model") or "unknown",
                            "input_tokens": usage.get("input_tokens", 0),
                            "output_tokens": usage.get("output_tokens", 0),
                            "cache_creation": usage.get("cache_creation_input_tokens", 0),
                            "cache_read": usage.get("cache_read_input_tokens", 0),
                        }
                    )
        except Exception as e:
            logger.debug("Error reading %s: %s", jsonl_file, e)

    entries.sort(key=lambda e: e["timestamp"])
    return entries


def _find_windows(entries: List[Dict[str, Any]]) -> List[datetime]:
    """Return the start timestamp of each 5-hour window.

    A new window starts whenever an entry falls at or after the current
    window's end time — not just on a 5-hour idle gap. This correctly
    handles a new message sent seconds after the previous window expired.
    """
    if not entries:
        return []
    starts = [entries[0]["timestamp"]]
    current_end = starts[0] + SESSION_DURATION
    for entry in entries[1:]:
        if entry["timestamp"] >= current_end:
            starts.append(entry["timestamp"])
            current_end = entry["timestamp"] + SESSION_DURATION
    return starts


def load_current_window(data_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Return usage data for the active (or most recent) 5-hour window."""
    path = Path(data_path).expanduser() if data_path else DATA_PATH
    entries = _load_all_entries(path)
    if not entries:
        return None

    window_starts = _find_windows(entries)
    if not window_starts:
        return None

    now = datetime.now(timezone.utc)

    # Find the most recent window that either contains now or is the last one
    current_start = window_starts[-1]
    current_end = current_start + SESSION_DURATION
    is_active = now < current_end

    # Entries belonging to this window
    window_entries = [
        e for e in entries if current_start <= e["timestamp"] < current_end
    ]

    # Per-model breakdown
    by_model: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                 "cache_creation": 0, "cache_read": 0}
    )
    for e in window_entries:
        key = _model_display(e["model"])
        m = by_model[key]
        m["calls"] += 1
        m["input_tokens"] += e["input_tokens"]
        m["output_tokens"] += e["output_tokens"]
        m["cache_creation"] += e["cache_creation"]
        m["cache_read"] += e["cache_read"]

    return {
        "window_start": current_start,
        "window_end": current_end,
        "is_active": is_active,
        "messages": len(window_entries),
        "by_model": dict(by_model),
        "loaded_at": now,
    }


def load_all_windows(data_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return summary data for every window (for history view)."""
    path = Path(data_path).expanduser() if data_path else DATA_PATH
    entries = _load_all_entries(path)
    if not entries:
        return []

    window_starts = _find_windows(entries)
    windows = []
    for ws in window_starts:
        we = ws + SESSION_DURATION
        w_entries = [e for e in entries if ws <= e["timestamp"] < we]
        windows.append(
            {
                "window_start": ws,
                "window_end": we,
                "messages": len(w_entries),
                "input_tokens": sum(e["input_tokens"] for e in w_entries),
                "output_tokens": sum(e["output_tokens"] for e in w_entries),
            }
        )
    return windows
