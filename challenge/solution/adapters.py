from typing import Any, Dict, Optional


def _normalize_provider_data(provider_value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not provider_value or not any(value is not None for value in provider_value.values()):
        return None
    return provider_value


def registry_adapter(company_name: str, responses: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    registry = responses.get(company_name, {}).get("registry")
    registry = _normalize_provider_data(registry)
    if not registry:
        return None

    return {
        "provider": "registry",
        "name": registry.get("name"),
        "role": registry.get("role"),
        "email": None,
        "phone": registry.get("phone"),
        "provider_confidence": None,
        "source_url": registry.get("source_url"),
    }


def listing_adapter(company_name: str, responses: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    listing = responses.get(company_name, {}).get("listing")
    listing = _normalize_provider_data(listing)
    if not listing:
        return None

    return {
        "provider": "listing",
        "name": listing.get("name"),
        "role": None,
        "email": None,
        "phone": listing.get("phone"),
        "provider_confidence": None,
        "source_url": listing.get("source_url"),
    }


def enrichment_adapter(company_name: str, responses: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    enrichment = responses.get(company_name, {}).get("enrichment")
    enrichment = _normalize_provider_data(enrichment)
    if not enrichment:
        return None

    provider_confidence = enrichment.get("provider_confidence")
    if provider_confidence is None:
        provider_confidence = 50

    return {
        "provider": "enrichment",
        "name": enrichment.get("name"),
        "role": None,
        "email": enrichment.get("email"),
        "phone": enrichment.get("phone"),
        "provider_confidence": provider_confidence,
        "source_url": enrichment.get("source_url"),
    }
