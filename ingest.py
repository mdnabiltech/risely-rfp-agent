import json
import os

REQUIRED_FIELDS = [
    "title", "institution", "product_fit",
    "is_higher_ed", "has_domain_fit", "has_workflow_fit",
    "has_expansion_potential", "has_strategic_value", "mentions_ai",
    "summary", "why_it_matches", "risks", "recommended_action",
]

WEB_RFPS_PATH = "data/web_rfps.json"


def load_rfps(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    records = data if isinstance(data, list) else [data]
    for record in records:
        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            title = record.get("title", "unknown")
            raise ValueError(f"Record '{title}' is missing required fields: {missing}")
    return records


def load_saved_web_rfps(path: str = WEB_RFPS_PATH) -> list[dict]:
    """Load previously discovered web RFPs from disk. Returns [] if file doesn't exist yet."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def append_web_rfp(rfp: dict, path: str = WEB_RFPS_PATH) -> None:
    """Append a newly discovered RFP to the web RFPs store on disk."""
    existing = load_saved_web_rfps(path)
    existing.append(rfp)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def load_rfps_from_web(existing_titles: set[str] | None = None) -> list[dict]:
    """
    Search the live web for RFPs using Tavily + Claude Haiku classification.
    Returns at most 1 new RFP that isn't already in existing_titles.
    Requires TAVILY_API_KEY and ANTHROPIC_API_KEY in the environment.
    """
    from tavily_search import search_and_classify
    candidates = search_and_classify(existing_titles=existing_titles)
    return [r for r in candidates if not any(f not in r for f in REQUIRED_FIELDS)]
