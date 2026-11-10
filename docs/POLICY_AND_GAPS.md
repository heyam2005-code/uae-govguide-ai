# Policy, standard, and gap traceability

| Source | Role in prototype | Evidence / design behavior | Limitation |
|---|---|---|---|
| UAE Federal Decree Law 45/2021, PDPL | Privacy | No identity number/passport number/doc image requested for test flow; avoid logging conversation text; optional cloud processing | This is a prototype design constraint, not a certified legal compliance assessment |
| UAE AI Strategy 2031 | Public-service digital transformation | Bilingual access, explainable guidance | No measured public impact study |
| UAE AI Adoption Guideline for Government Services | Human oversight and transparent AI | Highlight source uncertainty and human confirmation | Not an official government deployment |
| ICP Emirates ID service cards | Domain rules | Rules for applicant class, renewal, urgent pathway, documents, passport period | Static snapshot; confirm specific cases |
| ITU-T Y.3172 | Conceptual ML pipeline map | data ingestion -> retrieval/processing -> decision orchestration -> serving -> evaluation | Y.3172 targets ML architecture in future networks; not formal conformity |
| ITU AI Readiness Framework 2.0 | Open data, inclusion, infrastructure, governance | provenance, bilingual UI, evaluation logs | Qualitative mapping, not ITU rating or certification |
| EU GDPR Art.5 (global comparator) | Minimality principles | Example of privacy-by-design and retention minimization | Comparative example only; not UAE law |
| UK GDS API standards (global comparator) | Versioned public service data | Suggest centre service-coverage APIs and update timestamps | Design recommendation, not evidence of a UAE breach |

**Potential gaps (research hypotheses, not verified government failures):**
1. Machine-readable, category-scoped public-service eligibility rules and dependencies could reduce error-prone extraction.
2. Standardised centre service coverage (applicant categories, urgent intake, timestamps) would help prevent stale recommendations.
3. Cross-emirate residency dependencies may benefit from explicit versioned rule metadata.
4. Human verification and privacy minimisation remain important in high-impact identity-adjacent workflows.

**Observed document inconsistency:** `data/policy_conflicts.json` marks certain centre-page vs FAQ statements for manual review; the system excludes unverified cases from automatic recommendations. It is not evidence of non-compliance.

**Core provenance:** See `data/sources.json`, `data/policies.json`, `data/policy_conflicts.json`, `docs/policy_gap_hypotheses.json`.
