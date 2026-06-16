from pathlib import Path
from typing import Dict, List

from .adapters import enrichment_adapter, listing_adapter, registry_adapter
from .aggregator import aggregate_company, Candidate
from .loader import load_companies, load_mock_responses
from .scorer import score_candidate


OUTPUT_FIELDS = [
    "company_name",
    "contact_name",
    "contact_role",
    "contact_email_or_phone",
    "confidence_score",
    "source",
    "needs_human_review",
    "state",
]


def _pick_best_candidate(candidates: List[Candidate], company_name: str) -> Dict[str, object]:
    scored = []
    for candidate in candidates:
        score = score_candidate(candidate, company_name)
        scored.append((score, candidate))

    scored.sort(key=lambda item: (item[0], len(item[1].providers)), reverse=True)
    best_score, best_candidate = scored[0]
    return {
        "candidate": best_candidate,
        "confidence_score": best_score,
        "state": "VERIFIED" if best_score >= 70 else "LOW_CONFIDENCE",
    }


def run(csv_path: Path, json_path: Path) -> List[Dict[str, object]]:
    companies = load_companies(csv_path)
    responses = load_mock_responses(json_path)
    rows: List[Dict[str, object]] = []

    for company in companies:
        company_name = company["company_name"]
        registry = registry_adapter(company_name, responses)
        listing = listing_adapter(company_name, responses)
        enrichment = enrichment_adapter(company_name, responses)

        aggregation = aggregate_company(company_name, registry, listing, enrichment)
        if aggregation["state"] == "NOT_FOUND":
            rows.append(
                {
                    "company_name": company_name,
                    "contact_name": "",
                    "contact_role": "",
                    "contact_email_or_phone": "",
                    "confidence_score": 0,
                    "source": "",
                    "needs_human_review": True,
                    "state": "NOT_FOUND",
                }
            )
            continue

        if aggregation["state"] == "CONFLICTING":
            rows.append(
                {
                    "company_name": company_name,
                    "contact_name": "",
                    "contact_role": "",
                    "contact_email_or_phone": "",
                    "confidence_score": 0,
                    "source": " | ".join(aggregation["source_urls"]),
                    "needs_human_review": True,
                    "state": "CONFLICTING",
                }
            )
            continue

        best = _pick_best_candidate(aggregation["candidates"], company_name)
        candidate = best["candidate"]
        confidence_score = best["confidence_score"]
        state = best["state"]
        contact_channel = candidate.email or candidate.phone or ""
        if confidence_score < 70:
            contact_channel = ""

        rows.append(
            {
                "company_name": company_name,
                "contact_name": candidate.name or "",
                "contact_role": candidate.role or "",
                "contact_email_or_phone": contact_channel,
                "confidence_score": confidence_score,
                "source": " | ".join(aggregation["source_urls"]),
                "needs_human_review": confidence_score < 70,
                "state": state,
            }
        )

    return rows
