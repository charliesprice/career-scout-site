#!/usr/bin/env python3
"""Build a private, self-contained website from career-scout's saved research.

Reads <workspace>/data/{records,profile,calibration}.json (schema v1.x, see
SCHEMA.md in that folder) and writes ONE html file with the data embedded, so it
opens straight from disk with no server, no network and no install.

    python3 build_site.py --data ~/career-scout/data            # -> ~/career-scout/site/career-scout.html
    python3 build_site.py --data ./data --out /tmp/x.html --open
    python3 build_site.py --data ./data --check                 # validate only, write nothing

Prints a JSON summary (counts per view, warnings, output path) on stdout.
Standard library only; Python 3.9+.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "template.html"
PLACEHOLDER = "__CAREER_SCOUT_DATA__"
SUPPORTED_MAJOR = "1"

KINDS = {"job", "company"}
BUCKETS = {"match", "reach"}
STATUSES = {"new", "saved", "applied", "dismissed", "closed"}
WORKPLACES = {"remote", "hybrid", "onsite", "unknown"}

# Only these profile fields are shown on the site. Everything else in profile.json
# (experience, skills, interests...) stays out of the HTML file.
PROFILE_FIELDS = ["name", "headline", "education", "looking_for", "start_window",
                  "priorities", "hard_constraints", "locations", "target_industries",
                  "target_functions", "updated_at"]


def die(msg):
    print(json.dumps({"ok": False, "error": msg}, indent=2))
    sys.exit(1)


def read_json(path, default=None, required=False):
    """Read JSON, retrying briefly: career-scout may be rewriting the file right now."""
    if not path.exists():
        if required:
            die(f"{path} not found. Point --data at career-scout's data/ folder.")
        return default
    last = None
    for _ in range(5):
        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            last = e
            time.sleep(0.5)
    die(f"{path} is not valid JSON ({last}). If a career-scout run is writing it, wait and retry.")


def safe_url(u):
    return isinstance(u, str) and u.strip().lower().startswith(("http://", "https://"))


def view_of(r):
    """Each record lives in exactly one tab, so nothing shows up twice."""
    if r.get("kind") == "company" and r.get("watch_list") is True:
        return "watch"
    if r.get("bucket") == "reach":
        return "reach"
    return "openings" if r.get("kind") == "job" else "companies"


def check_record(r, warnings):
    rid = r.get("id") or "(no id)"
    label = f"{rid} {r.get('title', '')!r}"
    if not r.get("id"):
        warnings.append(f"{label}: missing id; status changes can't be tracked for it")
    if r.get("kind") not in KINDS:
        warnings.append(f"{label}: unknown kind {r.get('kind')!r}")
    if r.get("bucket") not in BUCKETS:
        warnings.append(f"{label}: unknown bucket {r.get('bucket')!r} (treated as match)")
    if r.get("status") not in STATUSES:
        warnings.append(f"{label}: unknown status {r.get('status')!r} (treated as new)")
    if r.get("workplace") not in WORKPLACES:
        warnings.append(f"{label}: unknown workplace {r.get('workplace')!r}")
    if not safe_url(r.get("url")):
        warnings.append(f"{label}: no usable http(s) link")
    if not isinstance((r.get("score") or {}).get("total"), (int, float)):
        warnings.append(f"{label}: no numeric score.total (shown as 0)")
    if r.get("kind") == "job":
        req = r.get("requirements")
        if not isinstance(req, dict):
            warnings.append("LEGACY_JOB")
        elif req.get("eligible") is False:
            warnings.append(f"{label}: requirements.eligible is false")
    if r.get("kind") == "company" and "entry_openings" not in r:
        warnings.append("LEGACY_COMPANY")


def latest_by_record(entries, id_key="record_id"):
    out = {}
    for e in entries or []:
        rid = e.get(id_key)
        if rid and (rid not in out or (e.get("at") or "") >= (out[rid].get("at") or "")):
            out[rid] = e
    return out


def build_payload(data_dir):
    records_doc = read_json(data_dir / "records.json", required=True)
    if isinstance(records_doc, list):  # tolerate a bare list
        records_doc = {"schema_version": "?", "records": records_doc}
    profile = read_json(data_dir / "profile.json", default={}) or {}
    calibration = read_json(data_dir / "calibration.json", default={}) or {}

    warnings = []
    version = str(records_doc.get("schema_version", "?"))
    if version.split(".")[0] != SUPPORTED_MAJOR:
        warnings.append(f"records.json schema_version {version!r}; this site was built for 1.x. "
                        "Fields may be missing or misread.")

    cal_scores = latest_by_record(calibration.get("entries"))
    cal_reach = latest_by_record(calibration.get("reach_reviews"))

    records = []
    seen_ids = set()
    for r in records_doc.get("records") or []:
        if not isinstance(r, dict):
            continue
        check_record(r, warnings)
        if r.get("id") in seen_ids:
            warnings.append(f"{r.get('id')}: duplicate id, later copy skipped")
            continue
        seen_ids.add(r.get("id"))
        user = r.get("user") or {}
        rating, reason = user.get("rating"), user.get("rating_reason")
        rating_from = "record" if rating is not None else None
        if rating is None and r.get("id") in cal_scores:
            e = cal_scores[r["id"]]
            rating, reason, rating_from = e.get("user_score"), e.get("reason"), "calibration"
        reach_valid, reach_note = user.get("reach_valid"), user.get("reach_reason")
        if reach_valid is None and r.get("id") in cal_reach:
            rv = cal_reach[r["id"]]
            reach_valid, reach_note = rv.get("valid"), rv.get("reason")
        rec = dict(r)
        rec["_view"] = view_of(r)
        rec["_user"] = {"rating": rating, "reason": reason, "from": rating_from,
                        "reach_valid": reach_valid, "reach_note": reach_note}
        records.append(rec)

    lj, lc = warnings.count("LEGACY_JOB"), warnings.count("LEGACY_COMPANY")
    warnings = [w for w in warnings if not w.startswith("LEGACY_")]
    if lj or lc:
        warnings.append(f"{lj} job(s) without `requirements` and {lc} compan(ies) without `entry_openings` "
                        "(saved before career-scout checked eligibility). The site marks them 'not checked'; "
                        "re-running career-scout refreshes them.")

    # Weights live on each record's score; take them from the first record that has them.
    weights = next(((r.get("score") or {}).get("weights_used") for r in records
                    if (r.get("score") or {}).get("weights_used")), {}) or {}

    entries = calibration.get("entries") or []
    deltas = [abs(e["delta"]) for e in entries if isinstance(e.get("delta"), (int, float))]
    cal_summary = {
        "rated": len(deltas),
        "mean_abs_gap": round(sum(deltas) / len(deltas), 1) if deltas else None,
        "lessons": [l.get("lesson") for l in (calibration.get("lessons") or []) if l.get("lesson")],
        "reach_reviews": len(calibration.get("reach_reviews") or []),
    }

    counts = {}
    for r in records:
        counts[r["_view"]] = counts.get(r["_view"], 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records_updated_at": records_doc.get("updated_at"),
        "schema_version": version,
        # Namespaces this workspace's browser storage without putting the path in the file.
        "store_key": hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()[:12],
        "profile": {k: profile.get(k) for k in PROFILE_FIELDS if k in profile},
        "weights": weights,
        "calibration": cal_summary,
        "records": records,
    }
    return payload, counts, warnings


def embed(payload):
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Make the JSON safe inside <script>: no "</script>", no "<!--", no JS line separators.
    text = (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        die(f"template {TEMPLATE} must contain {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, text)


def open_file(path):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            webbrowser.open(path.as_uri())
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="career-scout's data/ folder (holds records.json)")
    ap.add_argument("--out", help="output .html (default: <workspace>/site/career-scout.html)")
    ap.add_argument("--open", action="store_true", help="open the result in the default browser")
    ap.add_argument("--check", action="store_true", help="validate and summarize only; write nothing")
    a = ap.parse_args()

    data_dir = Path(a.data).expanduser()
    if data_dir.is_file():
        data_dir = data_dir.parent
    if not (data_dir / "records.json").exists() and (data_dir / "data" / "records.json").exists():
        data_dir = data_dir / "data"  # they pointed at the workspace root
    payload, counts, warnings = build_payload(data_dir)

    out = Path(a.out).expanduser() if a.out else data_dir.resolve().parent / "site" / "career-scout.html"
    summary = {
        "ok": True,
        "data": str(data_dir.resolve()),
        "records": len(payload["records"]),
        "views": {v: counts.get(v, 0) for v in ["openings", "companies", "reach", "watch"]},
        "hidden_by_default": sum(1 for r in payload["records"] if r.get("status") in ("closed", "dismissed")),
        "user_ratings": sum(1 for r in payload["records"] if r["_user"]["rating"] is not None),
        "records_updated_at": payload["records_updated_at"],
        "warnings": warnings,
    }
    if not a.check:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(embed(payload), encoding="utf-8")
        os.replace(tmp, out)
        summary["output"] = str(out.resolve())
        summary["bytes"] = out.stat().st_size
        if a.open:
            summary["opened"] = open_file(out.resolve())
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
