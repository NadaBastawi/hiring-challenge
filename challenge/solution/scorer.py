import re
from typing import Optional

from .aggregator import Candidate


def _normalize_company_name(company_name: str) -> str:
    normalized = re.sub(r"\b(llc|inc|co|corp|company|ltd|plc)\b", "", company_name, flags=re.IGNORECASE)
    normalized = re.sub(r"[^a-z0-9]", "", normalized.lower())
    return normalized


def _normalize_email_domain(email: str) -> str:
    if "@" not in email:
        return ""
    domain = email.split("@", 1)[1].lower()
    return re.sub(r"[^a-z0-9]", "", domain)


def enrichment_domain_matches_company(email: Optional[str], company_name: str) -> bool:
    if not email:
        return False
    company_token = _normalize_company_name(company_name)
    domain_token = _normalize_email_domain(email)
    if not company_token or not domain_token:
        return False
    return company_token in domain_token or domain_token in company_token


def is_generic_name(name: Optional[str]) -> bool:
    if not name:
        return False
    normalized = name.strip().lower()
    generic_tokens = {
        "office",
        "info",
        "contact",
        "sales",
        "support",
        "customer",
        "service",
        "admin",
        "team",
    }
    words = set(re.findall(r"[a-z]+", normalized))
    return bool(words & generic_tokens)


def _provider_base_score(candidate: Candidate) -> int:
    has_registry = "registry" in candidate.providers
    has_enrichment = "enrichment" in candidate.providers
    has_listing = "listing" in candidate.providers

    if has_registry and not has_enrichment and not has_listing:
        return 55
    if has_enrichment and not has_registry and not has_listing:
        return 50
    if has_listing and not has_registry and not has_enrichment:
        return 35
    if has_registry:
        return 55
    if has_enrichment:
        return 50
    return 35


def score_candidate(candidate: Candidate, company_name: str) -> int:
    score = _provider_base_score(candidate)
    if len(candidate.providers) >= 2:
        score += 20

    if candidate.email and enrichment_domain_matches_company(candidate.email, company_name):
        score += 10

    provider_confidence = candidate.provider_confidence or 50
    if provider_confidence >= 80:
        score += 15
    if provider_confidence < 50:
        score -= 15

    if len(candidate.providers) == 1 and is_generic_name(candidate.name):
        score -= 10

    score = max(0, min(100, int(round(score))))
    return score
