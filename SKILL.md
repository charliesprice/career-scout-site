---
name: career-scout-site
description: Turns career-scout's saved job-search research (records.json, profile.json, calibration.json) into a private, interactive website the user opens from their own computer, with tabs for openings, companies, reach picks and a watch list, filters (location, workplace, industry, function, type, seniority, score, status, deadline, date found), every card's score breakdown, eligibility, deadline and direct apply link, and Save / Applied / Dismiss buttons whose changes can be imported back into career-scout. Use this skill whenever the user wants to see, browse, filter or review their career-scout results, asks to "build", "make", "open", "refresh" or "rebuild" their job-search site, page or dashboard, wants to import status changes they exported from that site, or mentions career-scout-site, even if they just say "show me my jobs" after a career-scout run.
---

# career-scout-site

Builds one self-contained HTML file from career-scout's `data/` folder. The file
opens straight from disk: no server, no install, no internet. Its
Content-Security-Policy blocks every network request, so the user's personal data
never leaves their computer; links to postings open in a new tab.

Everything the site needs to know about the data is in the workspace's
`data/SCHEMA.md` (the contract career-scout writes). The bundled scripts already
implement it, so you rarely need to read it; consult it only when the data looks
unusual or the user asks for a change that depends on a field.

## Workflow

### 1. Find the data folder

career-scout keeps its workspace wherever the user chose (default
`~/career-scout`); the data is in `<workspace>/data/` next to `SCHEMA.md`. If the
user didn't say, look for it: check `~/career-scout/data`, then search likely
places (`find ~ -maxdepth 4 -name records.json -path '*data*'` and keep hits that
have a `SCHEMA.md` beside them). If several match, ask which one. If there's no
`records.json` at all, career-scout hasn't run yet: say so and offer to start it.

The data folder belongs to career-scout. Only read it, with one exception: step 2.

### 2. Import status changes (only when there are some)

Save / Applied / Dismiss clicks are stored in the browser, because a page opened
from disk can't write files. The page shows a bar at the bottom while any are
unsynced; its **Export for career-scout** button downloads
`career-scout-status-changes-<date>.json` (usually to `~/Downloads`).

Import when the user asks to, or when they ask to rebuild and exports newer than
the last build exist in `~/Downloads` (mention them and ask before applying):

```bash
python3 <skill>/scripts/apply_status.py <export.json> [more.json ...] --data <workspace>/data          # preview
python3 <skill>/scripts/apply_status.py <export.json> --data <workspace>/data --write                  # apply
```

Run the preview first and tell the user what will change. The script changes only
each record's `status`, writes atomically in career-scout's own format, and skips
a change as a **conflict** when career-scout has changed that record's status since
the user clicked (for example it found the posting closed). Explain any conflicts
and use `--force` only if the user wants their choice to win. If career-scout's
`scout.py set-status` is available you may use it instead, one record at a time;
the result is the same. Don't import while a career-scout search is running in
another session: both write `records.json`.

Then rebuild (step 3). On reload, the page sees the new statuses in the data and
clears the matching browser marks by itself. It also drops marks that conflicted
(the record's status changed underneath them), so the record's current status shows;
if the user still wants their choice, apply it with `--force` and rebuild.

### 3. Build

```bash
python3 <skill>/scripts/build_site.py --data <workspace>/data --open
```

- Output goes to `<workspace>/site/career-scout.html` unless `--out` is given. Keep
  that default: the file contains the user's data, it sits beside the data and
  outside any git repo, and the same path each time keeps the browser's saved marks
  and "new since last visit" memory working.
- `--check` validates and summarizes without writing anything.
- The script reads fresh every time, retries if career-scout is mid-write, and
  only embeds the profile fields the site displays (not experience, skills or
  `config.json`).
- It prints JSON: records per view, how many are hidden by default (closed or
  dismissed), how many carry the user's own rating, and `warnings`.

Python 3.9+ standard library only. If `python3` is missing, tell the user; don't
hand-build the page.

### 4. Tell the user what they're looking at

Keep it short and concrete, using the summary JSON:

- where the file is and that it's open (or how to open it: double-click it, or
  `open <path>` on a Mac);
- counts per tab, e.g. "9 openings, 2 reach picks, 17 on the watch list; 2
  dismissed items hidden";
- anything in `warnings` that matters, in plain words. Older records saved before
  career-scout checked eligibility show "Eligibility not checked"; a career-scout
  refresh fixes that;
- one line on saving marks: they live in this browser until exported, and "export,
  then ask me to import" makes them permanent.

Don't paste record contents into the chat; the page is where they're read.

## What the page shows (so you can answer questions about it)

- **At-a-glance tiles** at the top: how many things are open that the user can
  apply to, how many are due in 30 days, the next deadline, and how many are marked
  applied. Clicking one applies the matching filters.
- **Tabs.** Each record appears in exactly one: **Openings** (jobs, `bucket=match`),
  **Companies** (companies with entry-level openings now), **Reach picks**
  (`bucket=reach`, not on the watch list), **Watch list** (companies with
  `watch_list=true`, reach or not), plus **My list** (saved or applied, any tab)
  and **All**.
- **Filters** with live counts: search, score range, "only confirmed eligible",
  deadline (not passed / due in 30 days / has one / none), date found (including
  "new since my last visit"), status (closed and dismissed unticked by default),
  location (city, plus Remote), state/region, workplace, industry, function,
  employment type, seniority, organization type. Sort by score, deadline,
  newest, the user's rating, or name.
- **Each card:** fit score out of 10 (and "capped from X" when a dealbreaker
  applies), the user's own rating beside it when they gave one (from the record or,
  failing that, `calibration.json`), an eligibility box (jobs: `requirements`, with
  the evidence quote; companies: each `entry_openings` role as a direct link, or
  "no entry-level openings right now"), a deadline box (date, days left, red when
  passed), summary, reach reason, rationale, highlights and concerns, the full
  component breakdown in the user's priority order (estimated components marked),
  the posting / apply / careers links, and Save / Mark applied / Dismiss buttons.
  "More details" holds verification evidence, dates, alternate links and the
  user's notes.
- **"Refresh my search" button:** the page can't search (it never goes online), so the button shows the request to paste into Claude. If the user wants refreshes without asking, offer a scheduled task that runs a career-scout refresh and then `build_site.py`.
- **Header panels:** the user's ranked priorities with weights and dealbreakers,
  score accuracy from calibration with the lessons career-scout learned, and a
  short "about this page".

## Changing the site

If the user wants the page to look or behave differently, edit
`assets/template.html` in this skill (plain HTML/CSS/JS, no build step), keeping
the `__CAREER_SCOUT_DATA__` placeholder exactly once and the CSP meta tag, then
rebuild and check the result in a browser. Any text from the data must go through
`esc()` and any link through `okUrl()`: posting text comes from the web.

## Sharing or hosting

The default is private and local. If the user wants to put it online or send it
to someone, remind them it contains their profile headline, priorities, ratings and
notes, and confirm before publishing anything. A private option is to share the
single HTML file directly; it works offline on any computer.
