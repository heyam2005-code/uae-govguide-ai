"""Run labelled synthetic evaluation on the local, deterministic baseline.

Never call a cloud LLM, government site, or store conversation text. Output is
case-level measurements, not an estimate of accuracy on real citizens.
"""
from __future__ import annotations
import csv, json, os, sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# These evaluations must work on the offline baseline even when a developer has
# cloud environment variables set. Disable cloud explicitly for reproducibility.
for key in ('ENABLE_LLM','ALLOW_CLOUD_NLU','ALLOW_CLOUD_EXPLANATIONS'):
    os.environ[key] = '0'
from app.core import GovAgent
from app.dialogue import DialogueAgent

agent = GovAgent(enable_audit=False)
rows=[]

def record(group,code,description,expected,actual,ok):
    rows.append({'group':group,'case_id':code,'description':description,'expected':str(expected),
                 'actual':str(actual),'passed':bool(ok)})

# Classification (labelled in-repository queries)
intents = [
 ('I01','أريد تجديد الهوية الإماراتية','renew'),
 ('I02','I need to renew my Emirates ID','renew'),
 ('I03','فقدت هويتي وأحتاج بدل فاقد','replace'),
 ('I04','My Emirates ID was lost','replace'),
 ('I05','أحتاج إصدار الهوية لأول مرة','new'),
 ('I06','Need a new Emirates ID for the first time','new'),
]
for code,text,label in intents:
    got=agent.classify(text)
    record('intent',code,'Service intent detection',label,got,got==label)

# Retrieval recall@3: expected passage IDs and explicit user queries.
# Note: tiny curated, visible holdout; no broad domain-generalizability claim.
queries=[
 ('R01','رسوم تجديد بطاقة الهوية الإماراتية','renew','renew_fees'),
 ('R02','شروط أهلية تجديد الهوية قبل انتهاء البطاقة','renew','renew_eligibility'),
 ('R03','الوثائق المطلوبة لتجديد الهوية','renew','renew_documents'),
 ('R04','Replacement of a lost Emirates ID fees','replace','replace_fees'),
 ('R05','New Identity Card issuance documents','new','new_documents'),
 ('R06','Emirates ID renewal steps','renew','renew_step_1'),
]
for code,question,sid,expected in queries:
    docs=agent.kb.search(question,service_id=sid,limit=3)
    ids=[x['id'] for x in docs]
    record('rag_recall_at_3',code,'Relevant passage in top-3',expected,'|'.join(ids),expected in ids)

# Deterministic checks: no model is allowed to override policy engine.
base={'category':'citizen','age':29,'expiry_months':2,'passport_valid_months':12,
      'has_photo':True,'urgent':False,'emirate':'Dubai'}
policies=[
 ('P01',{},'stage','ready'),
 ('P02',{'urgent':True},'route','urgent_in_person'),
 ('P03',{'expiry_months':14},'flag','TOO_EARLY'),
 ('P04',{'passport_valid_months':1},'flag','PASSPORT_TOO_SHORT'),
 ('P05',{'has_photo':False},'flag','PHOTO_MISSING'),
 ('P06',{'category':'resident','expiry_months':8},'flag','TOO_EARLY'),
 ('P07',{'category':'citizen','passport_valid_months':1},'flag','COMBINED_RENEWAL_OPTION'),
 ('P08',{'passport_valid_months':1},'stage','needs_information'),
]
for code,changes,kind,expected in policies:
    profile=base|changes
    got=agent.answer('تجديد الهوية',service_id='renew',profile=profile)
    actual=got[kind] if kind in ('stage','route') else '|'.join(x['code'] for x in got['alerts'])
    passed=(actual==expected if kind in ('stage','route') else expected in actual.split('|'))
    record('policy',code,'Policy gate and route',expected,actual,passed)

# Facility ranking/eligibility; no geo-distance assumption.
loc=agent.locator
loc_cases=[
 ('C01',('Dubai','renew','citizen',False,'البرشاء'),'first','DXB-BARSHA'),
 ('C02',('Dubai','renew','resident',False,None),'count','0'),
 ('C03',('Dubai','replace','resident',False,None),'min_count','2'),
 ('C04',('Sharjah','renew','citizen',False,None),'count','0'),
 ('C05',('Dubai','new','citizen',True,None),'no_biometrics_only','true'),
 ('C06',('Ajman','renew','citizen',False,None),'count','0'),
 ('C07',('Dubai','renew','citizen',False,None),'no_distance','true'),
]
for code,(em,sid,cat,urgent,area),kind,expected in loc_cases:
    result=loc.recommend(em,sid,cat,urgent=urgent,area=area)
    centres=result['centres']
    actual=({'first':lambda:(centres[0]['id'] if centres else 'NONE'),
             'count':lambda:str(len(centres)),
             'min_count':lambda:str(len(centres)),
             'no_biometrics_only':lambda:str(all('NAHDA' not in x['id'] for x in centres)).lower(),
             'no_distance':lambda:str(all(x['distance_km'] is None for x in centres)).lower()})[kind]()
    passed=(int(actual)>=int(expected) if kind=='min_count' else actual==expected)
    record('locator',code,'Service-and-category grounded matching',expected,actual,passed)

# End-to-end conversations (synthetic non-identifying user personas)
conversations=[
 ('D01','أنا مواطن إماراتي في دبي البرشاء وبدي أجدد هويتي، وين أراجع؟',
    lambda r:r.get('centre_search') is not None and r['centre_search']['centres'][0]['id']=='DXB-BARSHA', 'Barsha first'),
 ('D02','أنا مقيم في دبي، وين أراجع لتجديد هويتي؟',
    lambda r:r.get('centre_search') is not None and not r['centre_search']['centres'] and 'لا يعني' in r['answer'], 'no false centre'),
 ('D03','أنا مواطن إماراتي عمري 29 في دبي وعندي صورة هويتي باقي شهرين وجوازي صالح سنة بدي تجديد عاجل، وين أراجع؟',
    lambda r:r['stage']=='ready' and r['route']=='urgent_in_person' and bool(r.get('centre_search')), 'urgent & centres'),
 ('D04','أنا مواطن إماراتي عمري 29 بدي أجدد عاجل ليش لازم أزور مركز ICP بدل التقديم أونلاين؟',
    lambda r:'تنص بطاقة خدمة ICP' in r['answer'] and r.get('centre_search') is None, 'why answer before missing slots'),
 ('D05','أنا مقيم في دبي عمري 29 هويتي باقي شهرين وجوازي باقي 12 شهر وعندي صورة وبدي أجدد عادي',
    lambda r:r['stage']=='ready' and r['route']=='standard_digital', 'resident digital guidance'),
]
for code,text,predicate,expected in conversations:
    r=DialogueAgent(GovAgent(enable_audit=False)).respond(text)
    passed=bool(predicate(r))
    actual=f"stage={r.get('stage')};route={r.get('route')};centre_count={len(r.get('centre_search',{}).get('centres',[])) if r.get('centre_search') else 'N/A'}"
    record('end_to_end',code,'Full dialogue and locator integration',expected,actual,passed)

# Source integrity and safety expectations (closed-world tests only).
sources=agent.sources
checks=[
 ('S01','ICP centre references all official',all(x['source_url'].startswith('https://icp.gov.ae/') for x in loc.centres)),
 ('S02','No fabricated coordinates',all(not x.get('latitude') and not x.get('longitude') for x in loc.centres)),
 ('S03','GhazaI points to Alghazal',next(x for x in loc.centres if x['id']=='DXB-GHAZAL')['source_url'].endswith('customer-happiness-center-alghazal/')),
 ('S04','Service source tracked',all(s['source_id'] in sources for s in agent.services.values())),
]
for code,desc,ok in checks:record('source_quality',code,desc,True,ok,ok)

summary={}
for name in sorted({r['group'] for r in rows}):
    subset=[r for r in rows if r['group']==name]
    summary[name]={'passed':sum(r['passed'] for r in subset),'total':len(subset),
                   'percent':round(100*sum(r['passed'] for r in subset)/len(subset),1)}
all_passed=sum(r['passed'] for r in rows)
results={'type':'offline labelled synthetic test suite','executed_on':'local deterministic mode',
         'as_of':date.today().isoformat(),'total_passed':all_passed,'total_cases':len(rows),
         'percent':round(100*all_passed/len(rows),1),'groups':summary,
         'notes':['Curated unit/scenario set; not population accuracy, not live ICP availability.',
                  'RAG recall@3 measured for six fixed labelled queries; no model-generated hallucination metric.',
                  'The cloud LLM integration was not tested in this evaluation.',
                  'No travel-distance or time-savings claims were measured.']}
out=ROOT/'artifacts';out.mkdir(exist_ok=True)
(out/'stage5_evaluation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
with (out/'stage5_cases.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
lines=['# UAE GovGuide AI — Stage 5 Offline Evaluation', '',
       f"**Observed:** {all_passed}/{len(rows)} checks passed ({results['percent']}%).", '',
       '| Dimension | Passed | Total | Percentage |','|---|---:|---:|---:|']
for name,g in summary.items():lines.append(f"| {name} | {g['passed']} | {g['total']} | {g['percent']}% |")
lines += ['', '**Interpretation:** These are manually labelled synthetic regression checks run against the deterministic offline baseline. '
          'They do not estimate real-world recommendation accuracy, hallucination rates, waiting times, or compliance in production.',
          '', '## Failures requiring investigation', '']
failures=[r for r in rows if not r['passed']]
lines += [f"- {r['case_id']} ({r['group']}): expected {r['expected']}; observed {r['actual']}" for r in failures] or ['No failures in this fixed test set.']
lines += ['', '## Known limitations', '',
          '- The repository covers a curated subset of ICP services and centres, not all UAE government services.',
          '- Distances, opening-now status, appointments, and geographic coordinates are not verified.',
          '- The six RAG queries are a tiny hand-labelled validation sample; use independent datasets for larger claims.',
          '- LLM cloud NLU and generative explanation require separate opt-in and independent red-team tests.',
          '- Human verification and the official ICP portal remain necessary before a trip or payment.',
          '', '## Source of truth', '',
          '- https://icp.gov.ae/en/services-details/?serviceid=64afe3c1035448005bd52e5d',
          '- https://icp.gov.ae/en/customer-happiness-centers/',
          '- https://icp.gov.ae/en/icp_centers/customer-happiness-center-alghazal/']
(ROOT/'docs'/'STAGE_5_EVALUATION_AR.md').write_text('\n'.join(lines),encoding='utf8')
print(json.dumps(results,ensure_ascii=False,indent=2))
