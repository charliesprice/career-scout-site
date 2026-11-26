# career-scout-site

A Claude skill that turns your [career-scout](https://github.com/charliesprice/career-scout)
research into a **private website you open from your own computer**: browse and
filter every opening and company it found, see at a glance whether you can apply
and when it's due, and jump straight to the posting.

## What you get

One HTML file (`<your career-scout folder>/site/career-scout.html`). Double-click it.

- **Tabs:** Openings · Companies (with entry-level roles open now) · Reach picks ·
  Watch list (good fits with nothing open yet) · My list (saved and applied) · All
- **Filters with live counts:** search, score range, "only roles I can apply to",
  deadline, date found ("new since my last visit"), status, city, state, workplace,
  industry, function, employment type, seniority, organization type
- **Every card:** fit score out of 10 with the full breakdown in your priority
  order and the reasoning, your own rating beside it when you gave one,
  **can-I-apply** (years of experience, degree, and the quote from the posting; for
  companies, each entry-level opening as a direct link), the **deadline** with days
  left, highlights and concerns, and **Apply / Open posting** buttons
- **Save / Mark applied / Dismiss** on each card

## Private by design

The page runs entirely on your computer. Its security policy blocks it from
loading or sending anything over the internet; the only network activity is when
you click a link to a posting. Nothing is hosted, and the file sits in your
career-scout folder, outside any git repo.

## How Save / Applied / Dismiss work (and the trade-off)

A web page opened from disk can't write to files, so your clicks are kept in your
browser (localStorage) and the page shows a bar at the bottom while any haven't
been synced. Click **Export for career-scout**, then tell Claude "import my status
changes". The skill writes them into `records.json`, the file career-scout owns, and
rebuilds the page.

- **Why not a local server that writes directly?** It would need to keep running
  and would add a moving part that can write your data. One static file is simpler
  and safer, and it opens anywhere.
- **The cost:** until you export, marks live only in that browser on that computer.
  Clearing browser data or switching browsers loses unexported marks.
- **Safety:** the import changes only `status`, and if career-scout changed a
  record since you clicked (for example the posting closed), it reports a conflict
  instead of overwriting.

## Getting new results

The page never goes online, so it can't run a search itself. Its **Refresh my search** button gives you the request to paste into Claude. To skip even that, ask Claude to schedule a weekly refresh (for example in the Claude desktop app's scheduled tasks). It runs career-scout and rebuilds the page, so new results are there when you open it.

## Install

**Claude Code / Claude Desktop (Code tab):**

```bash
git clone https://github.com/charliesprice/career-scout-site ~/.claude/skills/career-scout-site
```

Then, after a career-scout run, say "build my career-scout site".

**Claude.ai:** download the repo as a zip and upload it under Settings → Capabilities → Skills.

Requires Python 3.9+ (standard library only) and any modern browser.

## Using it

| Say | What happens |
|---|---|
| "build / open my career-scout site" | builds the page from your latest data and opens it |
| "refresh my site" (after a new career-scout run) | rebuilds; new results get a **New** tag |
| "import my status changes" | applies the exported file to career-scout, then rebuilds |

Or run the scripts yourself:

```bash
python3 scripts/build_site.py --data ~/career-scout/data --open
python3 scripts/apply_status.py ~/Downloads/career-scout-status-changes-*.json --data ~/career-scout/data          # preview
python3 scripts/apply_status.py ~/Downloads/career-scout-status-changes-*.json --data ~/career-scout/data --write  # apply
```

## Repo layout

```
SKILL.md                 # instructions Claude follows
scripts/build_site.py    # reads data/, embeds it in the template, writes one HTML file
scripts/apply_status.py  # imports exported status changes into records.json
assets/template.html     # the site: plain HTML/CSS/JS, no dependencies
evals/                   # test cases with fictional students (Jordan, Maya)
```

The data format is career-scout's `SCHEMA.md` (schema 1.x), copied into every
career-scout workspace as `data/SCHEMA.md`.

## Running the tests

```bash
claude plugin eval . --allow-tools Write,Edit,Bash --scaffold
```

## License

MIT
