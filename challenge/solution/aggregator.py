import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


NICKNAME_MAP = {
    "bob": "robert",
    "rob": "robert",
    "robby": "robert",
    "rick": "richard",
    "rich": "richard",
    "bill": "william",
    "billy": "william",
    "liz": "elizabeth",
    "beth": "elizabeth",
    "kate": "katherine",
    "katie": "katherine",
    "jen": "jennifer",
    "mike": "michael",
    "jim": "james",
    "jimmy": "james",
    "dan": "daniel",
    "dave": "david",
}


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = value.strip().lower()
    text = re.sub(r"[\.,;:\'\"\[\]\{\}/\\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_name(name: str) -> str:
    name = normalize_text(name)
    name = re.sub(r"\b(mr|mrs|ms|dr|miss|mx)\b\.??", "", name)
    return re.sub(r"[^a-z0-9\s]", "", name).strip()


def split_name(name: str) -> List[str]:
    normalized = normalize_name(name)
    return [token for token in normalized.split() if token]


def is_initial(token: str) -> bool:
    return len(token) == 1 or (len(token) == 2 and token.endswith("."))


def nickname_match(a: str, b: str) -> bool:
    a_norm = NICKNAME_MAP.get(a, a)
    b_norm = NICKNAME_MAP.get(b, b)
    return a_norm == b_norm


def jaro_distance(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions /= 2
    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3


def jaro_winkler(s1: str, s2: str, prefix_scale: float = 0.1, max_prefix: int = 4) -> float:
    jaro_score = jaro_distance(s1, s2)
    if jaro_score == 0.0:
        return 0.0

    prefix = 0
    for a, b in zip(s1, s2):
        if a == b:
            prefix += 1
        else:
            break
        if prefix == max_prefix:
            break

    return jaro_score + min(prefix, max_prefix) * prefix_scale * (1 - jaro_score)


def same_person(name_a: str, name_b: str) -> bool:
    if not name_a or not name_b:
        return False

    normalized_a = normalize_name(name_a)
    normalized_b = normalize_name(name_b)
    if normalized_a == normalized_b:
        return True

    tokens_a = split_name(name_a)
    tokens_b = split_name(name_b)
    if tokens_a and tokens_b and tokens_a[-1] == tokens_b[-1]:
        if tokens_a[0] == tokens_b[0]:
            return True
        if is_initial(tokens_a[0]) and tokens_b[0].startswith(tokens_a[0][0]):
            return True
        if is_initial(tokens_b[0]) and tokens_a[0].startswith(tokens_b[0][0]):
            return True
        if nickname_match(tokens_a[0], tokens_b[0]):
            return True

    return jaro_winkler(normalized_a, normalized_b) >= 0.92


def parse_role_from_listing_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    match = re.search(r"\(([^)]+)\)", name)
    if match:
        role_candidate = match.group(1).strip()
        return role_candidate.title()
    return None


def parse_role(role: Optional[str]) -> Optional[str]:
    if role:
        return role
    return None


def role_priority(role: Optional[str]) -> int:
    if not role:
        return 99

    normalized = normalize_text(role)
    if re.search(r"\b(accounts payable|ap manager|accounts payables?|a/p|ap)\b", normalized):
        return 1
    if re.search(r"\b(owner|founder|president|proprietor|ceo|co-founder|cofounder)\b", normalized):
        return 2
    if re.search(r"\b(cfo|chief financial|finance|controller|accounting|vp finance|vp of finance)\b", normalized):
        return 3
    if re.search(r"\b(office manager|manager|general manager|ops manager|operations manager|administrative manager)\b", normalized):
        return 4
    return 99


def _normalize_source_urls(urls: List[str]) -> List[str]:
    seen = set()
    unique_urls = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            unique_urls.append(url)
    return unique_urls


@dataclass
class Candidate:
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    providers: Set[str] = field(default_factory=set)
    source_urls: List[str] = field(default_factory=list)
    provider_confidence: Optional[int] = None

    @classmethod
    def from_provider(cls, provider_data: Dict[str, Optional[str]]) -> "Candidate":
        name = provider_data.get("name")
        role = provider_data.get("role") or parse_role_from_listing_name(name)
        return cls(
            name=name,
            role=role,
            email=provider_data.get("email"),
            phone=provider_data.get("phone"),
            providers={provider_data["provider"]},
            source_urls=[provider_data.get("source_url")] if provider_data.get("source_url") else [],
            provider_confidence=provider_data.get("provider_confidence"),
        )

    def merge(self, other: "Candidate") -> None:
        if not self.name and other.name:
            self.name = other.name
        if not self.role and other.role:
            self.role = other.role
        if self.role and other.role:
            self.role = self.role if role_priority(self.role) <= role_priority(other.role) else other.role
        self.email = self.email or other.email
        self.phone = self.phone or other.phone
        self.providers.update(other.providers)
        self.source_urls = _normalize_source_urls(self.source_urls + other.source_urls)
        if other.provider_confidence is not None:
            self.provider_confidence = max(self.provider_confidence or 0, other.provider_confidence)

    def score_context(self) -> Dict[str, Any]:
        return {
            "role_priority": role_priority(self.role),
            "provider_count": len(self.providers),
        }


def aggregate_company(
    company_name: str,
    registry_result: Optional[Dict[str, Optional[str]]],
    listing_result: Optional[Dict[str, Optional[str]]],
    enrichment_result: Optional[Dict[str, Optional[str]]],
) -> Dict[str, object]:
    provider_results = [result for result in (registry_result, listing_result, enrichment_result) if result is not None]
    if not provider_results:
        return {
            "candidates": [],
            "state": "NOT_FOUND",
            "source_urls": [],
        }

    named_results = [result for result in provider_results if result.get("name")]
    unnamed_results = [result for result in provider_results if not result.get("name")]

    candidates: List[Candidate] = []
    for provider_data in named_results:
        candidate = Candidate.from_provider(provider_data)
        merged = False
        for existing in candidates:
            if existing.name and candidate.name and same_person(existing.name, candidate.name):
                existing.merge(candidate)
                merged = True
                break
        if not merged:
            candidates.append(candidate)

    if len(candidates) > 1:
        # More than one distinct named candidate is a conflict
        source_urls = []
        for result in provider_results:
            url = result.get("source_url")
            if url:
                source_urls.append(url)
        return {
            "candidates": [],
            "state": "CONFLICTING",
            "source_urls": _normalize_source_urls(source_urls),
        }

    if candidates:
        main_candidate = candidates[0]
        for provider_data in unnamed_results:
            main_candidate.merge(Candidate.from_provider(provider_data))
        return {
            "candidates": [main_candidate],
            "state": "VERIFIED",
            "source_urls": _normalize_source_urls(main_candidate.source_urls),
        }

    merged_candidate = Candidate.from_provider(unnamed_results[0])
    for provider_data in unnamed_results[1:]:
        merged_candidate.merge(Candidate.from_provider(provider_data))

    return {
        "candidates": [merged_candidate],
        "state": "VERIFIED",
        "source_urls": _normalize_source_urls(merged_candidate.source_urls),
    }
