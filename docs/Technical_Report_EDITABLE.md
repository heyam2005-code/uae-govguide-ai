# UAE GovGuide AI — Technical Report Draft

**Prepared:** 10 November 2026 | **Intended for:** ITU AI for Good Lab UAE Hackathon | **Template status:** Draft; transfer to official ITU template before submission.

**Team:** [add team name and members] | **Repository:** [add public GitHub URL]

## 1. Executive overview and public-service use case

**Challenge.** Applicants navigating UAE government services can encounter category-dependent requirements, documentation needs and branch-specific processes. A useful assistant should not simply link to a centre: it should ask the right questions, justify each step and avoid falsely confirming eligibility.

**Solution.** UAE GovGuide AI is an independent Arabic/English prototype for official-source-grounded government service navigation. It turns an Emirates ID service request into a stateful, explained sequence of questions and steps; checks eligibility through transparent rules; and recommends documented customer-happiness centres compatible with the service, applicant class and stated locality.

**Scope.** Three ICP Emirates ID workflows are executable: issuance, renewal, and lost/damaged replacement. Two further catalogue entries are reference-only. The centre snapshot contains 13 documented records. The product does not transact with ICP or UAE PASS, accept identity documents, or make live booking or distance claims.

**Representative user journey.** A UAE citizen in Al Barsha, Dubai asks where to renew an Emirates ID. The assistant extracts citizen status and location, asks for age, ID expiration, passport validity and photo availability, then distinguishes standard online guidance from urgent in-person flow. It can explain why Al Barsha was matched and explicitly cautions that urgent intake must be confirmed with ICP.

**Public value hypothesis.** Structured eligibility and evidence-backed guidance may reduce avoidable visits and incomplete applications. Actual time-savings or user-outcome gains have not yet been measured.

## 2. Technical architecture and curated knowledge base

**Architecture.** Official ICP/UAE/ITU references -> manually curated source registry and machine-readable records -> normalization and policy labels -> reproducible knowledge chunks -> multilingual character n-gram TF-IDF retrieval -> stateful dialogue and deterministic policy validation -> centre matching -> browser/UI, REST API and audit events. Optional cloud language support is disabled by default.

**Knowledge base.** data/sources.json stores publisher, document URLs and access dates; data/services.json stores applicant-dependent service rules, fees and steps; data/policies.json stores policy, strategy and standards descriptions; data/kb.jsonl stores retrieval passages. data/centres_verified.csv records centre capability and confidence; data/policy_conflicts.json flags contradictions for manual review.

**Agent behaviour.** app/dialogue.py manages the session and clarification questions. app/core.py validates eligibility, documents and route changes. app/centre_guidance.py with app/locator.py finds service/category/emirate/locality-compatible centres and explains the rank. When evidence is missing, it withholds confident recommendations and refers users to ICP.

**Safety and audit.** Responses cite official sources, provide human confirmation caveats, and use synthetic non-identifying profiles. Audit events record policy codes and source references rather than full identity numbers. No ID number, passport number, document image, or UAE PASS credential is requested. Cloud processing requires explicit opt-in and additional privacy review before public use.

**Reproducibility.** FastAPI, Python, JSON/CSV, scikit-learn retrieval and pytest; Windows launch and repeatable tests are in README.md. The KB and the code can be inspected separately. There is no fine-tuning claim or official government API integration.

## 3. UAE governance, ITU mapping and safeguards

**UAE policy mapping.** The UAE Personal Data Protection Law is used to motivate minimised personal-data collection and restrained logging; the National AI Strategy 2031 and public-sector AI adoption guidance motivate accessible bilingual government support, transparency and human oversight. ICP service cards supply domain rules. UAE PASS is treated as an external official access channel, not an integrated authentication component.

**ITU-T Y.3172.** This recommendation concerns ML architecture for future networks. Our conceptual mapping parallels its separable lifecycle: source collection/data management; knowledge processing and retrieval; decision orchestration; serving/inference; monitoring and evaluation. This is an architectural analogy, NOT an assertion of Y.3172 formal conformance.

**ITU AI Readiness Framework 2.0.** Data readiness: source provenance and structured KB. Infrastructure: local-first FastAPI deployment, optional cloud processing. Skills and inclusion: Arabic/English dialogue and guided journey. Governance: source attribution, decision codes, uncertainty gating. Innovation: domain-specific, auditable agent design. The framework has not been used to issue a country readiness score.

**Accountability boundary.** The assistant issues informational guidance, not legally binding decisions; ICP remains the source of truth. Centre recommendations are not geodesic distance calculations, and official fees, rules, hours and urgent availability require confirmation prior to action.

**Global comparators.** EU GDPR Article 5 is cited only as an international privacy-design example; UK Government Digital Service API technical standards illustrate versioned, interoperable government data. Neither is treated as UAE law.

## 4. Progressive error scenario and policy/standards opportunities

**Scenario design.** A synthetic Emirati applicant, aged 29, in Al Barsha, Dubai requests urgent Emirates ID renewal. Events arrive sequentially. E1: ID expires in one month, passport has 12 months, photo is available. The agent selects the urgent in-person journey, matches an ICP centre on service/category/locality, and warns that actual urgent availability is unverified.

**E2 — missing prerequisite.** A later event reports that the required recent photo is unavailable. The policy gate changes the state from ready to needs_information and explains that the document must be prepared; it does not silently continue to a government transaction.

**E3 — changing document validity.** A later correction changes passport validity to one month. The agent withholds confirmation of standalone renewal eligibility and recommends verifying the combined ID/passport renewal pathway where applicable. The eligibility outcome is governed by the structured ICP policy snapshot, not improvised by a cloud model.

**Policy conflict handling.** Some published centre material appears to create ambiguity over service responsibilities. Related centre records are marked for human review rather than confidently recommended; policy_conflicts.json and source URLs preserve an audit trail. This is a source-level discrepancy and hypothesis, not a finding of government wrongdoing.

**Gaps to explore.** A machine-readable, versioned eligibility schema; published centre-level service/category/urgent-availability metadata; cross-emirate workflow dependency descriptions; a formal human-appeal and privacy-consent framework for AI guidance. Compare selected proposals with GDPR data minimisation and UK GDS government-data standards as nonbinding international examples.

## 5. Evaluation, reproducibility, constraints and references

**Testing.** The V5.1 repository passed 69/69 local pytest unit/integration tests (re-run 10 November 2026). A separate offline, fixed-label synthetic evaluation contains 36/36 passing cases: intent 6/6, locator 7/7, policy 8/8, retrieval recall@3 6/6, end-to-end 5/5, source-quality 4/4. This is only performance on a curated small set, not general real-world accuracy.

**Limitations.** Live government portal integration: none. External LLM: optional but not field-tested in the reported evaluation. Centres: no verified precise coordinates, travel-time routing, live queues, live opening status or urgent appointment availability. User time savings have not been estimated. Official data and changing rules may go stale.

**Reproducibility.** python -m pytest tests -q; python scripts/stage5_evaluate.py. Demo at /assistant; centre locator at /locator; structured policy simulation at /. The provided GitHub-ready folder includes code, data, tests, provenance and scenario documentation. Repo URL and team details must be added by the submitting team.

**Expected outcome.** A cautious, auditable policy-informed navigation layer able to explain when it has enough evidence to guide the user and when it should refuse to assert eligibility or centre availability. Future study should test diverse users, refresh official data, and independently review the privacy, safety and institutional workflows.

**Primary references.** ITU AI for Good UAE Hackathon: aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/ ; ICP renewal service: icp.gov.ae/en/services-details/?serviceid=64afe3c1035448005bd52e5d ; ICP centres: icp.gov.ae/en/customer-happiness-centers/ ; UAE policy and ITU source links in data/sources.json. EU GDPR and UK GDS references are strictly comparative.

