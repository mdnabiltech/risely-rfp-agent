"""
Live RFP discovery via Tavily.

Why Tavily instead of direct scraping?
Most procurement portals (BidNet, DemandStar, Bonfire, HigherGov premium) sit
behind authentication walls or JavaScript renderers that defeat plain HTTP
requests. Tavily's AI-powered search engine indexes and caches these pages,
returning clean text snippets we can actually read and classify — without
needing a subscription to each portal.

Each raw result is passed to Claude Haiku to extract the structured RFP schema
(booleans, product fit, risks, etc.) used by the existing scorer.
"""

import json
import os

import anthropic
from tavily import TavilyClient

# Queries covering Risely's three product areas: Enrollment, Advisor, Advancement.
# Quotes and OR operators narrow results toward actual RFP/solicitation pages.
RFP_QUERIES = [
    '"request for proposal" "enrollment management" "higher education" 2025',
    '"RFP" "student success" OR "student retention" platform university 2025',
    '"request for proposal" "academic advising" OR "student advising" college 2025',
    '"RFP" "student outreach" OR "student communication" university 2025',
    '"request for proposal" "alumni engagement" OR "donor outreach" university 2025',
    'site:bonfirehub.com OR site:rfpdb.com "higher education" enrollment advising 2025',
]

_CLASSIFY_PROMPT = """\
You are an RFP analyst for Risely, an AI platform for higher education institutions.
Risely sells three AI-agent products:
  1. Enrollment — AI outreach agents for recruiting, yield, and enrollment communications
  2. Advisor — automated advising nudges, early-alert workflows, caseload reduction
  3. Advancement — alumni engagement and donor-outreach automation

Analyze the web search result below and return ONLY valid JSON (no markdown fences,
no extra keys) that matches this schema exactly:

{{
  "title": "<concise RFP title>",
  "institution": "<institution name, or Unknown>",
  "product_fit": "<Enrollment | Advisor | Advancement>",
  "secondary_fit": "<optional second area — omit key entirely if none>",
  "due_date": "<YYYY-MM-DD, or empty string if unknown>",
  "is_higher_ed": true | false,
  "has_domain_fit": true | false,
  "has_workflow_fit": true | false,
  "has_expansion_potential": true | false,
  "has_strategic_value": true | false,
  "mentions_ai": true | false,
  "summary": "<2–3 sentence summary of the opportunity>",
  "why_it_matches": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "risks": ["<risk 1>", "<risk 2>"],
  "recommended_action": "<one-sentence next step for the Risely sales team>",
  "source_url": "{url}",
  "source": "Tavily Search"
}}

Field guidance:
- has_domain_fit: content is in enrollment, advising, student success, or advancement
- has_workflow_fit: the RFP describes outreach, communications, or a manual process an AI agent could own
- has_expansion_potential: touches a second Risely product area
- has_strategic_value: large public system, multi-campus, or uses cooperative purchasing

Search result to analyse:
Title: {title}
URL: {url}
Content snippet: {content}
"""


def _looks_like_rfp(raw: dict) -> bool:
    """Quick heuristic filter before spending an API call on classification."""
    text = f"{raw.get('title', '')} {raw.get('url', '')} {raw.get('content', '')}".lower()
    return any(kw in text for kw in ["rfp", "request for proposal", "solicitation", "procurement", "bid opening"])


def fetch_raw_results(max_per_query: int = 3) -> list[dict]:
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    seen: set[str] = set()
    results: list[dict] = []
    for query in RFP_QUERIES:
        resp = client.search(query, max_results=max_per_query, search_depth="advanced")
        for r in resp.get("results", []):
            if r["url"] not in seen:
                seen.add(r["url"])
                results.append(r)
    return results


def classify_result(raw: dict, client: anthropic.Anthropic) -> dict | None:
    prompt = _CLASSIFY_PROMPT.format(
        url=raw.get("url", ""),
        title=raw.get("title", ""),
        content=raw.get("content", "")[:2500],
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        text = msg.content[0].text.strip()
        # Strip markdown code fences if the model adds them despite instructions
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return None


def search_and_classify(existing_titles: set[str] | None = None) -> list[dict]:
    """
    Return the first RFP Tavily finds that isn't already in existing_titles.
    No domain/higher-ed filtering — used for prototyping.
    """
    known = {t.lower() for t in (existing_titles or set())}
    ant = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    for raw in fetch_raw_results():
        if not _looks_like_rfp(raw):
            continue
        rfp = classify_result(raw, ant)
        if not rfp:
            continue
        if rfp.get("title", "").lower() in known:
            continue
        return [rfp]

    return []
