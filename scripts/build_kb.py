"""Deterministic, auditable document-to-chunk ETL (no website scraping or API required)."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'data'
read=lambda x: json.loads((D/x).read_text(encoding='utf-8'))
sources={s['id']:s for s in read('sources.json')}
chunks=[]
def add(id,kind,source_id,service_id,title,text_en,text_ar,meta=None):
    assert source_id in sources
    chunks.append(dict(id=id,kind=kind,source_id=source_id,service_id=service_id,title=title,text_en=text_en,text_ar=text_ar,source_url=sources[source_id]['url'],checked_at=sources[source_id]['accessed_at'],metadata=meta or {}))
for s in read('services.json'):
 id=s['id'];src=s['source_id']
 add(id+'_intro','service',src,id,s['name_en'],s['description_en']+' Authority: '+s['agency']+' Channels: '+', '.join(s['channels']),s['description_ar']+' الجهة: الهيئة الاتحادية للهوية والجنسية والجمارك وأمن المنافذ')
 ar_labels={'eligibility':'شروط الأهلية ومتطلبات وشروط التجديد والإصدار', 'documents':'المستندات الوثائق الأوراق المطلوبة للتقديم والهوية', 'fees':'الرسوم التكلفة المبلغ الدفع'}
 for label,details in [('eligibility',s['eligibility']),('documents',s['documents']),('fees',s['fees'])]:
  body='; '.join(f'{k}: {v}' for k,v in details.items())
  add(id+'_'+label,label,src,id,s['name_en']+' '+label,body,s['name_ar']+' '+ar_labels[label]+' '+body)
 for i,step in enumerate(s['steps']):
  add(f'{id}_step_{i+1}','step',src,id,f'{s["name_en"]} step {i+1}',step['en'],step['ar'],{'step':i+1})
 for i,c in enumerate(s['caveats']):add(f'{id}_caveat_{i+1}','caveat',src,id,s['name_en']+' condition',c,c)
for p in read('policies.json'):
 add('policy_'+p['id'],'policy',p['source_id'],None,p['name'],p['summary_en']+' Design controls: '+'; '.join(p['design_rules']),p['summary_ar']+' '+p['summary_en'])
# Stage 4: geographic capability evidence. Do not extrapolate services from vicinity.
import csv
with (D/'centres_verified.csv').open(encoding='utf-8-sig',newline='') as f:
 for c in csv.DictReader(f):
  capability=f"Status: {c['status']}. Services: {c['services']}; renewal allowed: {c['renew_categories']}; replacement allowed: {c['replace_categories']}; new card allowed: {c['new_categories']}. Working hours: {c['hours']}."
  add('centre_'+c['id'],'centre',c['source_id'],None,c['name'],f"{c['address']}. {capability}",f"المركز {c['name']} في {c['emirate']}، العنوان {c['address']}. {capability}", {'emirate':c['emirate'],'status':c['status']})
with (D/'services_catalog.csv').open(encoding='utf-8-sig',newline='') as f:
 for c in csv.DictReader(f):
  if c['implementation_status']=='reference_only':
   add('catalog_'+c['service_id'],'service_catalog','catalog_'+c['service_id'],None,c['name_en'],f"ICP service discovery: {c['name_en']}. Reference only; no eligibility engine. {c['notes']}",f"خدمة حكومية: {c['name_ar']}. معلومات مرجعية فقط؛ غير مدعومة حاليًا بمحرك التحقق.")
(D/'kb.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in chunks),encoding='utf-8')
print('KB chunks:',len(chunks))
