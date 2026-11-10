"""Create 4-page technical-report draft (copy into ITU's official DOCX submission template)."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'docs'/'technical_report.pdf'
C=colors.HexColor
blue=C('#163f56');teal=C('#166a76');gray=C('#52687b');pale=C('#f0f5f7')
styles={
 'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=22,leading=26,textColor=blue,spaceAfter=12),
 'sub':ParagraphStyle('sub',fontName='Helvetica',fontSize=10.5,leading=15,textColor=gray,spaceAfter=12),
 'h':ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=teal,spaceBefore=11,spaceAfter=6),
 'p':ParagraphStyle('par',fontName='Helvetica',fontSize=9.1,leading=13.4,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='Helvetica',fontSize=8,leading=11.5,spaceAfter=5),
 'tiny':ParagraphStyle('tiny',fontName='Helvetica',fontSize=7.6,leading=10.5),
 'bullet':ParagraphStyle('bullet',fontName='Helvetica',fontSize=9,leading=13,spaceAfter=5,leftIndent=12,firstLineIndent=-9),
}
P=lambda s,k='p':Paragraph(s,styles[k])
story=[]
def p(t,k='p'):story.append(P(t,k))
def h(t):p(t,'h')
def bullet(t):p('&bull; '+t,'bullet')
def tbl(rows,widths=None):
    data=[[P(str(x),'tiny') for x in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pale),('TEXTCOLOR',(0,0),(-1,0),blue),('GRID',(0,0),(-1,-1),.35,C('#dbe4eb')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(t)

def page(canvas,doc):
    canvas.setStrokeColor(C('#dce7eb'));canvas.line(45,43,550,43)
    canvas.setFont('Helvetica',8);canvas.setFillColor(gray)
    canvas.drawString(45,30,'UAE GovGuide AI | ITU AI for Good Lab UAE | draft 09 Nov 2026')
    canvas.drawRightString(550,30,f'Page {doc.page}')

doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=43,bottomMargin=56,title='UAE GovGuide AI - Technical Report',author='UAE GovGuide AI Team')
# PAGE 1
p('UAE GovGuide AI','title')
p('Policy-aware government service navigation | Technical report draft | Public Services | 9 November 2026','sub')
h('1. Overview and use case')
p('UAE GovGuide AI is an independent, bilingual prototype that guides citizens and residents through selected UAE services. It combines an official-source knowledge base, source-attributed multilingual retrieval, stateful workflow steps, and deterministic checks for applicant eligibility and required documents. Its demonstration domain is the Emirates ID service family provided by the Federal Authority for Identity, Citizenship, Customs and Port Security (ICP). It does not transact with government systems or replace official decision-makers.')
p('The user describes a goal in everyday Arabic or English, selects non-identifying attributes such as applicant class and months remaining on an identity card or passport, and receives a service path with citations. When information changes, the agent reviews eligibility and may block unsafe next-step guidance instead of fabricating an approval.')
h('2. User needs and functional requirements')
bullet('<b>Clarity:</b> classify the service among renewal, first-time issuance, and replacement for a lost/damaged card; ask for clarification on mixed or unsupported intents.')
bullet('<b>Evidence:</b> link every government-specific recommendation to authoritative UAE sources; distinguish confirmed statements from conditional ones.')
bullet('<b>Workflow:</b> provide ordered steps, downloadable metadata and source IDs, and stop progression when a necessary precondition is missing.')
bullet('<b>Privacy:</b> use eligibility attributes without collecting identity/passport numbers, biometrics, or documents; avoid logging user message content.')
bullet('<b>Auditability:</b> expose discrete rules, citation IDs and actions as a reviewable decision trace (not a raw internal model reasoning transcript).')
bullet('<b>Human oversight:</b> direct the user to ICP for legal/eligibility ambiguities and all real transactions; never impersonate UAE PASS.')
h('3. Implemented MVP and data scope')
tbl([['Component','Current implementation'],['Official services','3 ICP service cards; category-dependent fees, prerequisites, required-document summaries and six workflow steps each'],['Knowledge base','44 indexed chunks, 13 source-catalogue entries, 6 local-policy / standards summaries'],['Location data','8 official ICP centre listings as emirate-level candidates; no fabricated coordinates or live opening hours'],['User experience','Arabic-first web UI, FastAPI REST service, local audit JSONL and progressive error scenario']],[125,380])
p('<b>Scope boundary:</b> the source catalogue is curated and dated 9 November 2026. The app must not be treated as a complete UAE government service catalogue.','small')
story.append(PageBreak())
# PAGE 2
p('Agent pipeline and standards mapping','title')
h('4. Architecture and data flow')
p('<b>Collection:</b> publicly accessible ICP service cards and UAE/ITU reference publications are curated into source-tagged JSON/CSV with review dates. <b>Transformation:</b> scripts convert each service summary, fee category, document group, step and condition into a retrievable JSONL chunk. <b>Retrieval:</b> character n-gram TF-IDF returns related Arabic/English passages and their official URLs. <b>Orchestration:</b> intent classification, service selection, applicant category checks, state-machine progression, and auditable policy gates run locally. <b>Serving:</b> REST API and browser interface. <b>Optional LLM:</b> an external model may paraphrase pre-approved text but may not override decisions; it is disabled by default.')
tbl([['Pipeline stage','Prototype component','Evidence / output'],['Data acquisition + validation','sources.json / services.json / policies.json','Original official URL, reviewed date, authority and explicit caveats'],['Preprocessing + index','scripts/build_kb.py / kb.jsonl','44 traceable document chunks'],['Inference and decision','KnowledgeBase / GovAgent in app/core.py','Retrieved context, policy flags, next action, source IDs'],['Serving and feedback','FastAPI + HTML UI; pytest + evaluate.py','Audit logs, synthetic policy-gate scores, human-visible references']],[126,185,194])
h('5. Conceptual mapping to ITU-T Y.3172')
p('Recommendation ITU-T Y.3172 specifies an ML architectural framework for <b>future networks including IMT-2020</b>, with pipeline, management and orchestration functions. It is not a public-service chatbot certification. Our alignment is an <b>architectural analogy</b>: source ingestion maps to data collection/preparation; the retrieval representation to an ML-related pipeline component; intent/policy orchestration to pipeline coordination; API serving and test scenarios to deployment/sandbox evaluation; audit traces to operational observability. Formal conformance is <b>not claimed</b>. [R8]')
h('6. ITU AI Readiness Framework 2.0 mapping')
tbl([['Readiness dimension','Evidence in the MVP / future obligation'],['Data','Provenance metadata; compact curated government-source KB; freshness gap documented'],['Digital infrastructure','Local deployable API and minimal dependencies; production security, cloud sizing and energy profiling remain unassessed'],['Digital skills','Arabic-first interface; clear instructions for student team, accessibility evaluation needed'],['Innovation ecosystem','Open-source-ready repo format; replicable chunking and test scripts'],['AI policy','UAE privacy/AI strategy mapping; human escalation; policy-gap hypothesis table and global comparators']],[145,360])
p('The 2026 ITU report uses dimensions, indices and metrics; this project supplies a <b>qualitative mapping</b> and does not calculate an official national readiness score. [R9]','small')
story.append(PageBreak())
# PAGE 3
p('Policy grounding and error simulation','title')
h('7. Local UAE policy and institutional mapping')
tbl([['Source','Design application'],['UAE PDPL / Federal Decree Law 45/2021','Data minimization, no identifiers, no photo/passport uploads or user utterance logging; require separate legal review before production. [R5]'],['UAE National AI Strategy 2031','AI use for more inclusive, accessible government services; public value and safeguards. [R6]'],['Government AI Adoption Guideline','Grounded output, measured evaluations and human oversight for uncertain cases. [R7]'],['UAE PASS / TDRA','UAE PASS enables sign-in to service providers; this app does not request credentials or submit claims on the user’s behalf. [R4]'],['ICP ID service cards','Different renewal windows and fees by category; photo, passport, biometric and urgent-centre conditions. [R1–R3]']],[170,335])
h('8. Progressive technical + policy error scenario')
p('<b>Scenario actor:</b> a synthetic adult UAE resident seeking ICP Emirates ID renewal in Dubai. Each event is disclosed only when the previous event has been processed; no real person data is collected.')
tbl([['Stage / newly released event','Expected decision','Observed local test'],['1. ID expires in 8 months; passport has 12 months validity','Block early renewal: non-UAE applicant window is under 6 months [R1]','TOO_EARLY'],['2. ID now expires in 2 months, passport in 2 months','Continue to block pending passport-validity review (ICP states at least 3 months) [R1]','PASSPORT_TOO_SHORT'],['3. Passport renewed to 18 months; recent photo unavailable','Hold next step and instruct user to prepare a new photo [R1]','PHOTO_MISSING']],[198,222,85])
h('9. Evaluation and auditability')
p('Repository automated checks: <b>12/12 unit tests passed</b> in the local test environment; mini-evaluation: <b>3/3 intent examples</b> and <b>3/3 staged policy gates</b> returned their expected classes/flags. These are deliberately <b>tiny synthetic test sets</b>, not an estimate of real-world classification precision, policy compliance, fairness, or travel-time savings. Evaluation artifacts can be re-generated with `python -m pytest -q` and `python scripts/evaluate.py`.')
p('Audit entries include a random session identifier, policy flag codes, retrieved chunk IDs, decision stage and source IDs; they omit raw user questions and profile values. A structured decision log makes design choices reviewable without disclosing a language model’s hidden internal reasoning.')
story.append(PageBreak())
# PAGE 4
p('Policy gaps, limitations and references','title')
h('10. Policy/standards gap hypotheses and global comparisons')
tbl([['Question to validate','Suggested design intervention','Global comparator'],['Category-specific requirements and cross-emirate dependencies may be hard to query as machine-readable data','Publish versioned requirements, authority, category, effective date and service dependencies','UK GDS API-first standards [R11]'],['Centre listing may not offer all live service capabilities and accessibility metadata required by autonomous routing','Provide authorized centre IDs, service scope, GeoJSON coordinates, current operating status and booking availability','UK GDS data/GeoJSON guidance [R11]'],['Identity-related AI could collect more data than needed','Use optional-category attributes, local policy checks, scoped retention, independent review and user consent for LLM processing','EU GDPR Art. 5 data minimisation [R10]']],[167,212,126])
p('<b>Important:</b> these are design and standards <b>hypotheses</b> requiring validation with the relevant authorities. We do not allege that a government entity breaches law or that an official legal conflict exists. The international references are comparators, not UAE obligations.')
h('11. Constraints and future work')
bullet('The knowledge base is small and manually curated. A production release requires source change monitoring, structured review and broader government-agency coverage.')
bullet('No direct ICP submission, UAE PASS authentication, official appointment scheduling or live queue integration is implemented.')
bullet('The centre selector filters by emirate; it does not claim nearest-centre accuracy because verified coordinates and live opening hours were not available for this dataset.')
bullet('The optional LLM only improves phrasing; robust bilingual understanding, formal safety assessment, secure deployment and population testing remain future work.')
h('12. References (official unless specified)')
references=[
('[R1] ICP renewal','https://icp.gov.ae/en/services-details/?serviceid=64afe3c1035448005bd52e5d'),
('[R2] ICP replacement','https://icp.gov.ae/en/services-details/?serviceid=64afe3c1035448005bd52e5b'),
('[R3] ICP first issue','https://icp.gov.ae/en/services-details/?serviceid=64afe3c1035448005bd52e5a'),
('[R4] UAE PASS','https://dgov.tdra.gov.ae/services/uae-pass'),
('[R5] UAE PDPL overview','https://u.ae/en/about-the-uae/digital-uae/data/data-protection-laws'),
('[R6] UAE AI strategy','https://u.ae/-/media/AI-publications/UAE-National-Strategy-for-Artificial-Intelligence-2031.pdf'),
('[R7] AI guideline','https://u.ae/-/media/AI-publications/AI-Adoption-Guideline-in-Government-Services-Eng.pdf'),
('[R8] ITU Y.3172','https://www.itu.int/itu-t/recommendations/rec.aspx?rec=13894'),
('[R9] ITU Readiness 2.0','https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf'),
('[R10] EU GDPR','https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng/'),
('[R11] UK GDS standards','https://www.gov.uk/guidance/gds-api-technical-and-data-standards'),
]
for label,url in references:
    p(f'<b>{escape(label)}</b> - <link href="{escape(url)}" color="#156a7d">{escape(url.split("/")[2])}</link>','small')
p('This report is a <b>standalone draft</b>. Transfer its contents into the hackathon’s official submission DOCX template if required.','small')
doc.build(story,onFirstPage=page,onLaterPages=page)
print(OUTPUT)
