# Risely RFP Monitor

Local pipeline for surfacing higher-education RFPs that match Risely's product suite (Enrollment, Advisor, Advancement).

## Browser UI

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. Shows all RFPs with priority badges, date status, filters by product/priority/status, and expandable detail cards.

## Terminal Pipeline

```bash
python3 main.py
```

Prints a scored, prioritized digest for every RFP in `data/rfps.json`.

## What This Is

A fully local, no-LLM pipeline. Drop RFP records into `data/rfps.json`, run either command, and get a scored digest of what's worth Risely's attention today.

## Why Records Are Manually Seeded

HigherGov is the intended discovery layer for finding higher-ed RFPs. Because HigherGov requires a login or free-trial account, Stage 1 does not scrape it. Instead, records are exported/copied from HigherGov and stored in `data/rfps.json`. PDFs downloaded from source portals go in `data/pdfs/`.

This is intentional: the core scoring and reporting logic should work and be testable before any external integrations are added.

## Pipeline Model

```
Collect/export from HigherGov or portal
        ↓
Normalize into rfps.json record
        ↓
Score deterministically (scorer.py)
        ↓
Surface in terminal report (main.py)
```

## Adding a Live Source

The pipeline is source-agnostic. `ingest.py` reads from a JSON file. To connect a live source, replace `load_rfps()` with a function that fetches from a HigherGov export, state procurement portal, or webhook — the scorer and UI need no changes.

## Adding a New RFP

Append a new object to `data/rfps.json`. Required fields:

| Field | Type | Description |
|---|---|---|
| `title` | string | RFP title |
| `institution` | string | Issuing institution |
| `product_fit` | string | Primary Risely product (Enrollment / Advisor / Advancement) |
| `is_higher_ed` | bool | Buyer is a higher-ed institution |
| `has_domain_fit` | bool | Content is in Risely's field: enrollment, advising/student-success, or advancement |
| `has_workflow_fit` | bool | Describes outreach, comms, support, or a manual process an agent could own |
| `has_expansion_potential` | bool | Also touches a second Risely product area |
| `has_strategic_value` | bool | Large public system, multi-campus buyer, or cooperative purchasing |
| `mentions_ai` | bool | Bonus — RFP explicitly asks for AI/automation (not required) |
| `summary` | string | 1–2 sentence description of what the RFP asks for |
| `why_it_matches` | list of strings | Bullet reasons this is a good fit |
| `risks` | list of strings | Risks or blockers to bidding |
| `recommended_action` | string | GO / MAYBE / PASS with rationale |

## Scoring Formula

We deliberately **do not require AI language**. Higher-ed institutions rarely ask for "AI" by name — they describe a recruitment, advising, or advancement problem and get sold on AI later. So the agent scores the **field** and the **workflow**; explicit AI language is only a small bonus.

| Criterion | Points |
|---|---|
| Domain fit — enrollment / advising / advancement | +30 |
| Workflow fit — outreach, comms, support, or a manual process an agent could own | +25 |
| Higher-ed buyer | +15 |
| Expansion potential into a second product area | +15 |
| Strategic value — large system, multi-campus, cooperative purchasing | +10 |
| AI/automation explicitly requested (bonus) | +5 |

**Priority thresholds:** 80–100 = High · 50–79 = Maybe · below 50 = Low

Risks are stored and displayed separately — they do not subtract from the score.

The three seeded records illustrate the spread: **WSU 100 (High)** — full domain + workflow + strategic; **CU Boulder 75 (Maybe)** — strong advising domain/workflow but single-institution, agent angle must be sold; **Allegheny 45 (Low)** — in our field but a CRM replacement with no agent-ownable workflow.

## Roadmap

| Stage | What Gets Added |
|---|---|
| ✅ 1 | Terminal pipeline — load, score, print |
| ✅ 2 | Streamlit browser UI — filter, card view, date status |
| 3 | PDF parsing with `pdfplumber` — extract text from downloaded RFP documents |
| 4 | LLM classification via Claude API — replace manual flags with AI-derived scoring |
| 5 | Automated daily digest — HigherGov API or portal scrape → email/Slack alert |
| 6 | Deployment — hosted URL, scheduled refresh, multi-user |
