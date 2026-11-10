"""Stage 4 dataset QA; reproducible, offline, no speculative geocoding."""
import csv,json
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parents[1]
with (P/'data'/'centres_verified.csv').open(encoding='utf-8-sig',newline='') as f:c=list(csv.DictReader(f))
with (P/'data'/'services_catalog.csv').open(encoding='utf-8-sig',newline='') as f:s=list(csv.DictReader(f))
sources={x['id'] for x in json.loads((P/'data'/'sources.json').read_text(encoding='utf8'))}
errors=[]
for label,rows in [('centres',c),('services',s)]:
 key='id' if label=='centres' else 'service_id'
 if len(set(x[key] for x in rows))!=len(rows):errors.append('duplicate '+label+' IDs')
for row in c:
 if not row['source_url'].startswith('https://icp.gov.ae/'):errors.append('nonofficial URL: '+row['id'])
 if row['source_id'] not in sources:errors.append('missing source_id: '+row['id'])
 if row['status'] not in ('active','closed_for_maintenance','service_verification_needed'):errors.append('unknown status: '+row['id'])
 if row['latitude'] or row['longitude']:errors.append('unverified coordinates entered: '+row['id'])
 if 'renew' in row['services'].split('|') and not row['renew_categories']:errors.append('missing renewal categories: '+row['id'])
 if row['status']=='active' and not row['hours']:errors.append('missing hours: '+row['id'])
for row in s:
 if row['implementation_status'] not in ('guided','reference_only'):errors.append('unexpected implementation status: '+row['service_id'])
 if row['source_url'].startswith('https://icp.gov.ae/') is False:errors.append('nonofficial catalog url: '+row['service_id'])
summary={'reviewed_at':'2026-11-09','centre_rows':len(c),'active_centres':sum(x['status']=='active' for x in c),
 'closed_centres':sum(x['status']=='closed_for_maintenance' for x in c), 'pending_manual_review':sum(x['status']=='service_verification_needed' for x in c),
 'biometrics_only':sum(x['services']=='biometrics' for x in c),
 'emirates_covered_in_curated_data':sorted(set(x['emirate'] for x in c)),
 'services_in_catalog':len(s),'guided_services':sum(x['implementation_status']=='guided' for x in s),
 'reference_only_services':sum(x['implementation_status']=='reference_only' for x in s),
 'centre_sources_present':sum(x['source_id'] in sources for x in c),
 'verified_coordinates':0,'real_distance_calculations_supported':False,
 'hours_listed':sum(bool(x['hours']) for x in c),'errors':errors,
 'limitation':'A documented subset of ICP centres, not exhaustive. No verified coordinates. Hours and service availability may change.'}
(P/'artifacts'/'stage4_data_quality.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
if errors:raise SystemExit(1)
