#!/usr/bin/env python3
"""Apply status changes exported from the career-scout site to records.json.

The site can't write files, so Save / Applied / Dismiss marks live in the browser
until the user clicks "Export for career-scout", which downloads
career-scout-status-changes-<date>.json. This script writes those marks into
<workspace>/data/records.json, the file career-scout owns.

    python3 apply_status.py ~/Downloads/career-scout-status-changes-*.json --data ~/career-scout/data           # preview
    python3 apply_status.py ~/Downloads/career-scout-status-changes-*.json --data ~/career-scout/data --write   # apply

Safe by default: without --write nothing changes. A change is skipped as a
conflict if the record's status in records.json is no longer the one the user saw
when they made the mark (career-scout changed it since, e.g. marked it closed);
--force applies it anyway. Only `status` is touched. Several export files can be
passed at once; for the same id the most recent change wins.
Standard library only; Python 3.9+.
"""
import argparse
import json
import sys
import time
from pathlib import Path

STATUSES = {"new", "saved", "applied", "dismissed", "closed"}
FORMAT = "career-scout-status-changes"


def die(msg):
    print(json.dumps({"ok": False, "error": msg}, indent=2))
    sys.exit(1)


def load(path):
    for _ in range(5):
        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            err = e
            time.sleep(0.5)
    die(f"{path} is not valid JSON ({err})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="+", help="exported career-scout-status-changes-*.json file(s)")
    ap.add_argument("--data", required=True, help="career-scout's data/ folder")
    ap.add_argument("--write", action="store_true", help="actually update records.json")
    ap.add_argument("--force", action="store_true", help="apply even when records.json changed since the mark")
    a = ap.parse_args()

    data_dir = Path(a.data).expanduser()
    if not (data_dir / "records.json").exists() and (data_dir / "data" / "records.json").exists():
        data_dir = data_dir / "data"
    rec_path = data_dir / "records.json"
    if not rec_path.exists():
        die(f"{rec_path} not found")

    latest = {}
    for p in a.exports:
        doc = load(Path(p).expanduser())
        if not isinstance(doc, dict) or doc.get("format") != FORMAT:
            die(f"{p} is not a career-scout status export (expected format {FORMAT!r})")
        for c in doc.get("changes") or []:
            cid = c.get("id")
            if cid and (cid not in latest or (c.get("changed_at") or "") >= (latest[cid].get("changed_at") or "")):
                latest[cid] = c

    records_doc = load(rec_path)
    by_id = {r.get("id"): r for r in records_doc.get("records", [])}
    applied, unchanged, conflicts, problems = [], [], [], []
    for cid, c in sorted(latest.items()):
        to, base = c.get("to"), c.get("from")
        r = by_id.get(cid)
        row = {"id": cid, "title": c.get("title"), "from": base, "to": to}
        if to not in STATUSES:
            problems.append({**row, "reason": f"invalid status {to!r}"})
        elif r is None:
            problems.append({**row, "reason": "id not in records.json"})
        elif r.get("status") == to:
            unchanged.append(row)
        elif base is not None and r.get("status") != base and not a.force:
            conflicts.append({**row, "now": r.get("status"),
                              "reason": "records.json changed since this mark; rerun with --force to apply anyway"})
        else:
            row["was"] = r.get("status")
            r["status"] = to
            applied.append(row)

    if a.write and applied:
        # Same on-disk format as career-scout's own save_json (indent 2, UTF-8, trailing newline).
        tmp = rec_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(records_doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        tmp.replace(rec_path)

    print(json.dumps({
        "ok": True,
        "written": bool(a.write and applied),
        "dry_run": not a.write,
        "applied": applied, "already_set": unchanged, "conflicts": conflicts, "problems": problems,
        "next": ("Rebuild the site so the page picks up the new statuses."
                 if a.write and applied else
                 "Preview only. Rerun with --write to apply." if applied else "Nothing to apply."),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
