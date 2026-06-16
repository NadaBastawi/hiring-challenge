# PLAN.md — Contact Finder

## Architecture

**Goal**: given `company_name` + `mailing_address`, return a best-guess decision-maker contact per row with full provenance, a confidence score, and an explicit state for every case — including "not found".

**Default target persona**: AP manager / accounts payable first, then owner / founder for small businesses, then CFO / finance lead for larger ones, then office manager as a last fallback. Legal owner from registry is used for identity corroboration, not as the primary contact target.

**Data flow**:

1. **Normalisation** — Parse address into components (street, city, state, zip). Strip legal suffixes from company name (LLC, Inc, Corp, Co.). Generate a stable lookup key per company for deduplication downstream.

2. **Source fan-out** — Query all three tiers in parallel via pluggable adapters. Each adapter returns `RawContact[] | NotFound`. No adapter blocks another.

3. **Aggregation & deduplication** — Group results by company. Fuzzy-match contact names across sources (Jaro-Winkler ≥ 0.92). Three outcomes: (a) same person in 2+ sources → merge into single record, both sources in provenance, corroboration bonus applied; (b) single candidate from one source → pass through as `LOW_CONFIDENCE` candidate pending scoring; (c) two or more non-matching candidates for the same company → mark `CONFLICTING`, preserve all candidates in provenance, route to human review regardless of individual scores.

4. **Confidence scoring** — Per-field scoring with source-reliability weights, cross-source corroboration bonus, and staleness penalty (detailed below).

5. **Output** — One row per company: `contact_name`, `contact_role`, `contact_email_or_phone`, `confidence_score` (0–100), `source` (pipe-delimited provenance chain), `needs_human_review` (bool). When confidence < 70: `contact_email_or_phone = ""` and `needs_human_review = true`. Every cannot-verify state is an explicit, first-class output — never a silent null.

**Design principles**:
- Every output field is tagged with its source adapter and query. No field is ever inferred without a traceable origin.
- "Not found" is a valid output state, not a failure to hide.
- Adapters are pluggable: adding a new source requires no changes to the core scoring or aggregation logic.

---

## Sources & Strategy

Three tiers, queried in parallel:

| Tier | Type | Rationale | Confidence Weight | How it fails |
|------|------|-----------|-------------------|--------------|
| 1 | Public business registries (SoS, LLC filings) | Authoritative owner of record; public data, no ToS risk | High | Often lists a registered agent or silent partner, not the operational payer; data can lag months behind actual ownership changes |
| 2 | Licensed commercial enrichment (Apollo / Clearbit-style) | Broad coverage, role data, verified emails | Medium-High | Goes stale; role titles inconsistent; small businesses under-indexed relative to mid-market |
| 3 | Public directories (BBB, Yelp, Google Places) | Phone numbers; corroboration signal on name/address | Medium-Low | Phone often reaches a front desk, not a named contact; no role data |

**Strategy**: fan out to all tiers in parallel, then aggregate. Don't short-circuit on the first hit — cross-validation *is* the confidence engine. A contact appearing in 2+ independent sources earns a significant corroboration bonus.

Tier 1 establishes legal identity. Tier 2 adds operational role and a contact channel. Tier 3 provides phone as an alternative channel and a cross-check on name/address accuracy.

**What I would NOT use**: personal social profiles (Facebook, Instagram), LinkedIn without an API agreement (ToS violation), any provider that cannot state a provenance guarantee for its data.

---

## Quality

### Deduplication
- Normalize names: lowercase, strip titles (Mr./Ms./Dr.), strip punctuation.
- Fuzzy-match within the same company's result set using Jaro-Winkler.
- "John Smith" + "J. Smith" from two sources → merge into one record; both sources listed in provenance.

### Confidence Scoring (0–100)

**Base score by source tier:**
- Registry only → 55
- Commercial enrichment only → 50
- Directory only → 35

**Modifiers:**
- +20 if 2+ independent sources agree on the same person
- +10 if email domain matches the company's apparent domain
- −10 if name is very common (collision risk, single source)
- −15 if source data is >18 months old

**Threshold**: `needs_human_review = true` and `contact_email_or_phone = ""` when confidence < 70.Precision over recall is the explicit success metric — a high human-review rate on hard rows is a good result, not a failure.

### Provenance
Every output row carries a `source` field: a pipe-delimited chain of which adapter(s) contributed each piece of data.
Example: `registry:CA-SOS | enrichment:apollo-mock`
No field is output without a source tag. Ever.

### Cannot-Verify States
Three explicit states, not nulls:

| State | Meaning | Output behaviour |
|-------|---------|-----------------|
| `NOT_FOUND` | No candidate returned from any source | Included in output; routed to human queue |
| `LOW_CONFIDENCE` | Candidate found, score < threshold | Included; `needs_human_review = true` |
| `CONFLICTING` | Multiple sources disagree on identity | Included; `needs_human_review = true`; all candidates listed in provenance |

**False-positive risk**: contacting the wrong person is treated as more damaging than missing a contact. When in doubt, flag for human review rather than surfacing a low-confidence result as clean.

---

## Privacy / Compliance

**Would do:**
- Query public business registries (public record by definition).
- Use licensed commercial providers with explicit B2B data agreements.
- Collect only business contact info tied to a business role — US B2B only.
- Respect `robots.txt` and ToS of every web source.
- Record provenance for every output value; log all data sources for full auditability.
- Support opt-out / suppression: any individual or company on a suppression list is excluded before output, not after.

**Would NOT do:**
- Collect personal cell numbers or home addresses.
- Scrape LinkedIn or social platforms in violation of ToS.
- Use data sourced from breaches or grey-market aggregators.
- Retain enriched contact data beyond the operational need.
- Contact individuals who have opted out of business directories.

**Compliance default**: treat all data as CCPA-governed (strictest US standard). Any account with a registered address suggesting EU presence is flagged and excluded from automated enrichment until legal confirms permissible sources under GDPR.

---

## Clarifying Questions

### Q1 — Who is the target persona: legal owner of record, or operational payer?

**Why it matters**: A Secretary of State filing gives us the legal owner — verifiable, but potentially a silent partner or investor who never touches invoices. An AP manager or office manager is the actual driver of payment but significantly harder to find in public data. These two targets require different source hierarchies.

**Default assumption**: target the person most likely to authorize or process payment — AP manager > owner/founder > CFO/finance lead > office manager. Fall back to legal owner only if no operational contact is found.

**What changes depending on your answer**: If "legal owner only" → Tier 1 (registry) becomes the primary source; Tier 2 becomes corroboration only. This flips the source priority order in the aggregation step and simplifies the role-matching logic. If "AP/operations manager is top priority" → Tier 2 (commercial enrichment, which carries role data) becomes primary; registry becomes identity corroboration. The role-filter in the aggregation step becomes the most important ranking signal.

---

### Q2 — When enrichment provides a role title (e.g., "Manager", "AP Lead"), how do you weight it in the ranking if corroboration is missing?

**Why it matters**: Enrichment tools often return role data, but it can be stale, inferred, or mismatched against your target personas. If enrichment says "Manager" but registry says "Owner", and only one source has a phone number, you need a tiebreaker rule. This determines whether role > name or name > role as the primary signal.

**Default assumption**: Role data from enrichment is a *signal* but not authoritative on its own. If name matches across sources but roles conflict, prioritize the highest-rank role in our target hierarchy (AP > Owner > CFO > Office). If roles don't conflict, use role match as a +15 bonus to confidence (higher than generic corroboration).

**What changes depending on your answer**: If "role data is highly reliable (pre-verified by enrichment)" → role becomes the primary ranking signal; name-matching becomes secondary. This raises the confidence floor for enrichment-only hits. If "role data is noisy, trust name-matching first" → name becomes primary; role is a tie-breaker only. This keeps enrichment-only hits lower confidence (50 base) and requires corroboration to cross 70.

---

### Q3 — Is there an existing data provider contract I must stay within, and are any accounts in EU/UK jurisdictions?

**Why it matters**: If a commercial enrichment contract already exists (e.g. Apollo, ZoomInfo, Clearbit), I should build and prioritize that adapter first rather than designing for arbitrary providers. EU/UK presence changes the permissible source set substantially under GDPR and may require a lawful basis assessment before any enrichment is run.

**Default assumption**: US-only accounts; no existing provider contract; I design adapters as pluggable and prioritize sources in tier order.

**What changes depending on your answer**: Existing contract → I build that adapter first, treat it as the primary Tier 2 source, make others optional fallbacks. EU/UK accounts present → only GDPR-certified providers, explicit data minimization, no opportunistic web enrichment; those rows are flagged and excluded from automated enrichment until legal confirms a permissible basis.
