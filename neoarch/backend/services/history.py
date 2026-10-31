"""Pacman transaction history parsed from /var/log/pacman.log."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

PACMAN_LOG = "/var/log/pacman.log"

_LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s+\[ALPM\]\s+(?P<msg>.*)$")
_EVENT_RE = re.compile(
    r"^(?P<action>installed|upgraded|downgraded|reinstalled|removed)\s+"
    r"(?P<name>\S+)\s+\((?P<detail>[^)]*)\)$"
)

_ACTIONS = {
    "installed": "install",
    "upgraded": "upgrade",
    "downgraded": "downgrade",
    "reinstalled": "reinstall",
    "removed": "remove",
}


def _parse_timestamp(text: str) -> Optional[datetime]:
    text = text.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    try:
        return datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _parse_event(msg: str) -> Optional[Dict]:
    match = _EVENT_RE.match(msg)
    if not match:
        return None
    action = _ACTIONS[match.group("action")]
    detail = match.group("detail").strip()
    old = new = ""
    if "->" in detail:
        old, _, new = detail.partition("->")
        old, new = old.strip(), new.strip()
    else:
        new = detail
    return {
        "action": action,
        "name": match.group("name"),
        "version": new,
        "old_version": old,
    }


def read_history(path: str = PACMAN_LOG, limit: int = 200,
                 max_bytes: int = 4_000_000) -> List[Dict]:
    """Return pacman transactions, newest first.

    Each transaction is ``{"timestamp": datetime | None,
    "packages": [{"action", "name", "version", "old_version"}]}``.
    Only the last ``max_bytes`` of the log are read so a large log never
    stalls the caller; unreadable logs yield an empty list and ``limit``
    caps the result.
    """
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            start = max(0, size - max_bytes)
            fh.seek(start)
            raw = fh.read()
    except OSError:
        return []

    text = raw.decode("utf-8", errors="replace")
    if start > 0:
        text = text.split("\n", 1)[-1]
    lines = text.splitlines()

    transactions: List[Dict] = []
    current: Optional[Dict] = None
    last_ts: Optional[datetime] = None

    for line in lines:
        match = _LINE_RE.match(line.strip())
        if not match:
            continue
        ts = _parse_timestamp(match.group("ts")) or last_ts
        msg = match.group("msg").strip()

        if msg.startswith("transaction started"):
            if current and current["packages"]:
                transactions.append(current)
            current = {"timestamp": ts, "packages": []}
            last_ts = ts
            continue
        if msg.startswith("transaction completed") or msg.startswith("transaction committed"):
            if current is not None:
                transactions.append(current)
                current = None
            continue

        event = _parse_event(msg)
        if event is None:
            continue
        if current is None:
            current = {"timestamp": ts, "packages": []}
        current["packages"].append(event)
        last_ts = ts

    if current and current["packages"]:
        transactions.append(current)

    transactions = [t for t in transactions if t["packages"]]
    transactions.reverse()
    if limit:
        transactions = transactions[:limit]
    return transactions


def package_history(name: str, path: str = PACMAN_LOG,
                    limit: int = 200) -> List[Dict]:
    """Return the transactions that touched one package, newest first.

    Each entry has the same shape as :func:`read_history` but only the
    events for ``name`` remain in ``packages``.
    """
    name = (name or "").strip()
    if not name:
        return []
    entries: List[Dict] = []
    for transaction in read_history(path, limit=0):
        events = [p for p in transaction["packages"] if p.get("name") == name]
        if events:
            entries.append({"timestamp": transaction["timestamp"],
                            "packages": events})
    if limit:
        entries = entries[:limit]
    return entries


def history_stats(transactions: List[Dict]) -> Dict[str, int]:
    """Count transactions and package events by action."""
    stats = {"transactions": len(transactions), "install": 0, "upgrade": 0,
             "remove": 0, "downgrade": 0, "reinstall": 0}
    for transaction in transactions:
        for package in transaction["packages"]:
            action = package.get("action", "")
            if action in stats:
                stats[action] += 1
    return stats
