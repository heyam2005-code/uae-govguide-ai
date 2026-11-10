"""Audit seed data quality and export a tidy service-by-category analytical table."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data';OUT=ROOT/'artifacts';OUT.mkdir(exist_ok=True)
read=lambda f:json.loads((D/f).read_text(encoding='utf-8'))
sources=read('sources.json');services=read('services.json');policies=read('policies.json')
with (D/'centres.csv').open(encoding='utf-8-sig',newline='') as f:centres=list(csv.DictReader(f))
source_ids={s['id'] for s in sources};error=[]
if len(source_ids)!=len(sources):error.append('duplicate source IDs')
if len({s['id'] for s in services})!=len(services):error.append('duplicate service IDs')
for s in services:
 if s['source_id'] not in source_ids:error.append(f"missing source {s['id']}")
 if len(s['steps'])!=6:error.append(f"unexpected workflow step count {s['id']}")
 for cat in ['citizen','resident','gcc']:
  if cat not in s['documents']:error.append(f"missing category docs {s['id']} {cat}")
for p in policies:
 if p['source_id'] not in source_ids:error.append(f"missing policy source: {p['id']}")
for c in centres:
 if c['source_id'] not in source_ids:error.append('missing centre source')
rows=[]
for s in services:
 for cat in ['citizen','resident','gcc']:
  rows.append({'service_id':s['id'],'service_name_en':s['name_en'],'applicant_category':cat,'agency':s['agency'],'documents_summary':' | '.join(s['documents'][cat]),'fee_schedule_json':json.dumps(s['fees'],ensure_ascii=False),'source_id':s['source_id'],'official_service_link':next(z['url'] for z in sources if z['id']==s['source_id']),'source_checked_at':s['source_checked_at']})
with (D/'services_analytical.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
report={'service_count':len(services),'source_count':len(sources),'policy_count':len(policies),'centre_count':len(centres),'indexed_chunks':len((D/'kb.jsonl').read_text().splitlines()),'analytical_rows':len(rows),'source_id_reference_integrity':not error,'centre_coordinates_present':sum(bool(c['coordinates']) for c in centres),'centre_hours_verified':sum(c['hours']!='not independently verified' for c in centres),'errors':error,'notes':'Centre coordinate/hour completeness reflects intentionally missing unverified data; it is not silently imputed.'}
(OUT/'data_quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if error:raise SystemExit(1)
