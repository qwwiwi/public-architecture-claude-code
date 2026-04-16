#!/usr/bin/env python3
"""
Auto-create tasks from curiosity-gaps.md for HOMER.

Parses curiosity-gaps.md, finds OPEN gaps owned by HOMER,
creates tasks in task-ledger.md, and marks gaps as assigned.
"""
import re
import uuid
from datetime import datetime
from pathlib import Path

# Paths relative to repo root (one level up from scripts/)
BASE = Path(__file__).parent.parent
WORKSPACE_BASE = BASE.parent.parent / "workspaces" / "homer"
GAPS = WORKSPACE_BASE / "memory" / "curiosity-gaps.md"
LEDGER = WORKSPACE_BASE / "task-ledger.md"

SEP = "\n---\n"
KV_RE = re.compile(r"^\s*([\w-]+)\s*[:=]\s*(.*)$")


def parse_blocks(text: str) -> list[str]:
    """Split markdown on '---' separator."""
    return [b.strip() for b in text.split(SEP) if b.strip()]


def parse_kv(block: str) -> dict:
    """Extract key:value pairs and title from markdown block."""
    data = {}
    lines = block.splitlines()

    # Extract title from first markdown header if present
    for ln in lines:
        if ln.strip().startswith("#"):
            data.setdefault("title", ln.strip().lstrip("#").strip())
            break

    # Extract key:value pairs
    for ln in lines:
        m = KV_RE.match(ln)
        if m:
            k, v = m.group(1).strip(), m.group(2).strip()
            data[k.lower()] = v

    return data


def extract_id(block: str) -> str | None:
    """Extract id field from a block."""
    for ln in block.splitlines():
        m = KV_RE.match(ln)
        if m and m.group(1).lower() == "id":
            return m.group(2).strip()
    return None


def update_status(block: str, new_status: str, task_id: str | None = None) -> str:
    """Update status in a block, optionally adding assigned_task."""
    lines = block.splitlines()
    out = []
    seen_status = False
    seen_task = False

    for ln in lines:
        m = KV_RE.match(ln)
        if m and m.group(1).lower() == "status":
            out.append(f"status: {new_status}")
            seen_status = True
        elif m and m.group(1).lower() == "assigned_task":
            if task_id:
                out.append(f"assigned_task: {task_id}")
                seen_task = True
            else:
                out.append(ln)
        else:
            out.append(ln)

    if not seen_status:
        out.append(f"status: {new_status}")
    if task_id and not seen_task:
        out.append(f"assigned_task: {task_id}")

    return "\n".join(out)


def load_text(path: Path) -> str:
    """Read file text, return empty if not found."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def ensure_file_exists(path: Path) -> None:
    """Ensure parent directory and file exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Task Ledger\n\n", encoding="utf-8")


def create_task_entry(gap: dict, task_id: str) -> str:
    """Create a task entry for the ledger."""
    title = gap.get("title") or gap.get("description", "Research task")
    gap_id = gap.get("id", "unknown")
    owner = gap.get("owner", "HOMER")
    created = datetime.utcnow().isoformat() + "Z"

    entry = f"""{SEP}id: {task_id}
title: {title}
status: OPEN
assignee: {owner}
created_at: {created}
source_gap: {gap_id}

## Objective
Research the following gap:
{gap.get("description", "No description available")}

## Context
- Gap ID: {gap_id}
- Owner: {owner}

## Research Approach
{gap.get("research approach", "No research approach defined")}

## Deliverable
Store research findings in memory and update gap status to insight_stored.
"""
    return entry


def main() -> None:
    """Main entry point."""
    # Ensure task-ledger exists
    ensure_file_exists(LEDGER)

    # Load gaps
    text = load_text(GAPS)
    if not text:
        print(f"[curiosity_loop] No curiosity-gaps.md found at {GAPS}")
        return

    blocks = parse_blocks(text)
    updated_blocks = []
    assigned = []

    for block in blocks:
        meta = parse_kv(block)

        owner = meta.get("owner", "").upper()
        status_raw = meta.get("status", "").strip().upper()
        gap_id = meta.get("id", extract_id(block) or "unknown")

        # Check if this is an OPEN gap owned by HOMER
        if owner == "HOMER" and (status_raw == "OPEN" or status_raw == ""):
            task_id = f"T-{uuid.uuid4().hex[:8]}"

            # Add to task ledger
            with LEDGER.open("a", encoding="utf-8") as f:
                f.write(create_task_entry(meta, task_id))

            # Update gap block
            block = update_status(block, "task_assigned", task_id)

            assigned.append({
                "task_id": task_id,
                "title": meta.get("title", "(no title)"),
                "gap_id": gap_id,
            })

        updated_blocks.append(block)

    # Write updated gaps back
    GAPS.parent.mkdir(parents=True, exist_ok=True)
    GAPS.write_text(SEP.join(updated_blocks), encoding="utf-8")

    # Print summary
    if assigned:
        print("[curiosity_loop] Assigned tasks:")
        for a in assigned:
            print(f"  - {a['task_id']}: {a['title']} (gap={a['gap_id']})")
    else:
        print("[curiosity_loop] No new tasks assigned.")


if __name__ == "__main__":
    main()