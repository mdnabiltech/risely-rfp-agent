from datetime import date

# Positive-only scoring. We score whether an RFP sits in Risely's FIELD and
# describes a WORKFLOW an agent could own — not whether it asks for "AI" by name.
# Higher-ed institutions rarely request AI explicitly; they describe a
# recruitment / advising / advancement problem and get sold on AI later. So
# domain + workflow fit dominate, and explicit AI language is only a small bonus.
SCORE_WEIGHTS = {
    "has_domain_fit":          30,  # content is in enrollment / advising / advancement
    "has_workflow_fit":        25,  # outreach, comms, support, or manual process an agent could run
    "is_higher_ed":            15,  # institutional higher-ed buyer
    "has_expansion_potential": 15,  # also touches a second Risely product area
    "has_strategic_value":     10,  # large public system, multi-campus, or cooperative purchasing
    "mentions_ai":              5,  # bonus only: explicitly asks for AI / automation
}


def assign_priority(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 50:
        return "Maybe"
    return "Low"


def _date_status(due_date_str: str) -> tuple[str, int | None]:
    if not due_date_str:
        return "Unknown", None
    due = date.fromisoformat(due_date_str)
    delta = (due - date.today()).days
    if delta < 0:
        return "Closed", delta
    if delta <= 14:
        return "Due Soon", delta
    return "Open", delta


def score_rfp(record: dict) -> dict:
    score = sum(points for field, points in SCORE_WEIGHTS.items() if record.get(field))
    date_status, days_remaining = _date_status(record.get("due_date", ""))
    return {
        **record,
        "score": score,
        "priority": assign_priority(score),
        "date_status": date_status,
        "days_remaining": days_remaining,
    }
