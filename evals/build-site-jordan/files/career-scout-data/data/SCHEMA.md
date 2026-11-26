# career-scout data format (schema v1.0)

This file is copied into every workspace as `data/SCHEMA.md`. It is the contract
between career-scout, which writes the data, and any skill or app that reads it,
such as a website that lets the user browse and filter results. Read this file and
the JSON files beside it. No other context is needed.

## Files in `data/`

| File | What it is | Readers |
|---|---|---|
| `records.json` | Every job and company found, scored and verified | Website: main data |
| `profile.json` | The user's structured profile: priorities, constraints, target roles | Website: "about you" panel, score explanations |
| `calibration.json` | User's own scores versus the agent's, reach reviews, lessons | Website: optional "how accurate is this" panel |
| `search_log.json` | Runs, queries and job boards searched, with dates | Internal (dedupe) |
| `seen.json` | Index of every posting/company already evaluated | Internal (dedupe) |

All files are UTF-8 JSON. Dates are ISO 8601 (`2026-10-31` or
`2026-10-31T14:00:00+00:00`). `config.json` in the workspace root holds the user's
email and is **not** for display.

## `records.json`

```json
{
  "schema_version": "1.0",
  "updated_at": "2026-10-31T14:00:00+00:00",
  "records": [ <Record>, ... ]   // sorted by score.total, highest first
}
```

### Record

One shape for both jobs and companies, so a single list can be filtered.

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable. `job_xxxxxxxxxx` or `co_xxxxxxxxxx`. Safe as a URL slug / React key |
| `kind` | `"job"` \| `"company"` | **Job** = a specific opening you can apply to. **Company** = an organization worth exploring, openings or not |
| `bucket` | `"match"` \| `"reach"` | **Reach** = tangential to stated interests but plausibly appealing; see `reach_reason` |
| `title` | string | Job title, or company name for company records |
| `company` | object | `{name, website, stage, size, description}`; `stage` ∈ startup, growth, large, public_sector, nonprofit, academic, unknown |
| `summary` | string | 1–3 sentences: what the role or company is, in plain language |
| `url` | string | The posting (jobs) or the careers/home page (companies). Always opened by the agent before saving |
| `alternate_urls` | string[] | Same job found elsewhere (e.g. LinkedIn copy of a Greenhouse post) |
| `apply_url` | string? | Direct application link if different from `url` |
| `source` | object | `{name, ats, board, ats_id, found_via}`; `name` ∈ greenhouse, lever, ashby, workday, linkedin, handshake, company_site, sector_board, web_search, other |
| `locations` | object[] | `[{city, region, country}]`; any key may be null. Empty list = unknown |
| `workplace` | enum | remote, hybrid, onsite, unknown |
| `industries` | string[] | From the **industry vocabulary** below. At least one |
| `functions` | string[] | From the **function vocabulary**. Required for jobs; optional for companies (main hiring areas) |
| `employment_type` | enum | full_time, internship, fellowship, part_time, contract, unknown (jobs) |
| `seniority` | enum | internship, entry, associate, mid, senior, unknown (jobs) |
| `compensation` | object? | `{min, max, currency, period, source, text}`; `period` ∈ year, hour, month, stipend; `source` ∈ posted, estimated. `null` if unknown |
| `posted_date` | date? | When the posting went up, if known |
| `deadline` | date? | Application deadline, if known |
| `score` | object | See below |
| `reach_reason` | string? | Reach records only: why this is worth a look despite not being an obvious fit |
| `highlights` | string[] | 2–4 short reasons this fits the user, written to the user ("Uses your music production background") |
| `concerns` | string[] | Honest drawbacks ("Posted salary below your floor") |
| `tags` | string[] | Free-form keywords for search |
| `requirements` | object | Jobs: `{min_years_experience, degree, eligible, evidence}`, what the posting asks for and whether the user qualifies |
| `entry_openings` | object[] | Companies: `[{title, url}]`, entry-level roles open now, each a direct link |
| `watch_list` | boolean | Companies with no current entry-level openings: worth knowing, not yet actionable |
| `status` | enum | new, saved, applied, dismissed, closed. A website may let the user change this |
| `user` | object | `{rating, rating_reason, reach_valid, reach_reason}`; the user's own judgment, null until given |
| `verification` | object | `{method, evidence, verified_at, last_check}`; `method` ∈ ats_api, page_opened, search_result_opened |
| `dates` | object | `{found, last_seen, last_verified, closed}` |
| `first_run` | string | Which search run found it |

### `score`

| Field | Type | Notes |
|---|---|---|
| `total` | number | 0.0–10.0, one decimal. **The headline score.** Already capped if a hard constraint is violated |
| `uncapped_total` | number | Score before the constraint cap |
| `components` | object | `{priority_key: 0–10}`, one per priority in `profile.json`. Good for a breakdown bar or radar chart |
| `weights_used` | object | `{priority_key: weight}`; weights sum to 1 |
| `constraint_violations` | string[] | Hard constraints broken (e.g. `"salary below floor"`). Non-empty means capped |
| `rationale` | string | One or two sentences explaining the score |
| `estimated` | string[] | Components scored on estimates rather than posted facts (e.g. `["compensation"]`) |
| `missing_components` | string[] | Priorities that were not scored (treated as 5) |

### Industry vocabulary

`technology, finance, investing, consulting, healthcare, life_sciences, education,
government_policy, nonprofit_social_impact, media_entertainment, sports, music,
arts_design, consumer_retail, energy_climate, manufacturing_hardware, real_estate,
legal, aerospace_defense, transportation_logistics, hospitality_food,
agriculture_food_systems, telecommunications, research_academia, gaming,
marketing_advertising, architecture_construction, fashion_beauty, other`

### Function vocabulary

`software_engineering, data_analytics, data_science_ml, product_management, design,
research, consulting_strategy, finance_investing, operations, marketing,
sales_business_development, communications_pr, policy, education_teaching,
healthcare_clinical, legal, writing_content, people_hr, project_management,
entrepreneurship, engineering_hardware, creative_production, customer_success, other`

For display, convert keys to labels by replacing `_` with a space and title-casing,
e.g. `nonprofit_social_impact` → "Nonprofit Social Impact".

## `profile.json`

```json
{
  "name": "First name (optional)",
  "headline": "One-sentence summary of who the user is and what they want",
  "education": {"school": "", "majors": [], "minors": [], "graduation": "2027-05"},
  "looking_for": ["full_time", "internship"],
  "start_window": {"earliest": "2027-06", "latest": "2027-09"},
  "priorities": [
    {"key": "location", "rank": 1, "label": "Location", "preference": "NYC first, Boston second, no remote-only"},
    {"key": "compensation", "rank": 2, "label": "Compensation", "preference": "$85k+ base"}
  ],
  "hard_constraints": [
    {"key": "salary_floor", "description": "Base salary at least $60k", "value": 60000}
  ],
  "locations": {"preferred": ["New York, NY"], "acceptable": ["Boston, MA"], "excluded": [], "remote": "acceptable"},
  "target_industries": ["music", "media_entertainment"],
  "avoid_industries": ["aerospace_defense"],
  "target_functions": ["product_management", "data_analytics"],
  "target_titles": ["Associate Product Manager", "Business Analyst"],
  "interests": ["live music", "audio engineering"],
  "values": ["creativity", "honesty"],
  "work_style": {"collaboration": "high", "structure": "medium", "pace": "fast", "hours_per_week": "45-50"},
  "fulfillment_drivers": ["creative output", "visible impact on users"],
  "long_term_goals": ["Lead product at a music-tech company"],
  "seed_companies": ["Spotify", "SoundCloud"],
  "search_plan": {"queries": [], "ats_boards": [], "reach_themes": []},
  "settings": {"constraint_cap": 3.0},
  "updated_at": "2026-10-31"
}
```

`priorities[].key` matches the keys in each record's `score.components`. Use
`label` and `preference` to explain a score breakdown to the user.

## Suggested website behavior

- Views: **Openings** (`kind=job, bucket=match`), **Companies**
  (`kind=company, bucket=match, watch_list=false`), **Reach** (`bucket=reach`),
  and a separate **Watch list** (`watch_list=true`) of companies to check back on.
- Filters: location (city/region/country), workplace, industry, function,
  employment type, seniority, compensation range, score range, status, date found.
- Hide `status=closed` by default, and show a "new since last visit" marker using `dates.found`.
- Show `score.total` prominently, with the component breakdown, `highlights`,
  `concerns` and `rationale` on the detail view.
- Where `user.rating` exists, show it beside the agent's score.
- The data is the user's private information. Build the site to run locally or
  privately rather than on a public host, unless the user chooses otherwise.
