from ingest import load_rfps
from scorer import score_rfp

DATA_PATH = "data/rfps.json"
WIDTH = 62


def print_report(rfp: dict) -> None:
    bar = "─" * WIDTH
    print(bar)
    print(f"  {rfp['title']}")
    print(f"  {rfp['institution']}")
    print(bar)
    print(f"  Product Fit   {rfp['product_fit']}")
    print(f"  Score         {rfp['score']} / 100")
    print(f"  Priority      {rfp['priority']}")
    days = rfp.get("days_remaining")
    if rfp["date_status"] == "Closed" and days is not None:
        status_label = f"Closed ({abs(days)} days overdue)"
    elif rfp["date_status"] == "Due Soon" and days is not None:
        status_label = f"Due Soon ({days} days remaining)"
    elif rfp["date_status"] == "Open" and days is not None:
        status_label = f"Open ({days} days remaining)"
    else:
        status_label = rfp["date_status"]
    print(f"  Status        {status_label}")
    print()
    print("  Summary")
    print(f"    {rfp['summary']}")
    print()
    print("  Why It Matches")
    for item in rfp["why_it_matches"]:
        print(f"    • {item}")
    print()
    print("  Risks")
    for item in rfp["risks"]:
        print(f"    • {item}")
    print()
    print("  Recommended Action")
    print(f"    {rfp['recommended_action']}")
    print()


def main() -> None:
    rfps = load_rfps(DATA_PATH)
    scored = sorted([score_rfp(r) for r in rfps], key=lambda r: r["score"], reverse=True)
    print()
    print("  RISELY RFP MONITOR — Stage 1")
    label = "opportunity" if len(scored) == 1 else "opportunities"
    print(f"  {len(scored)} {label} loaded")
    print()
    for rfp in scored:
        print_report(rfp)


if __name__ == "__main__":
    main()
