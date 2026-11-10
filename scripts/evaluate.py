"""Run reproducible synthetic scenarios. Output is observed only, no fabricated benchmarks."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core import GovAgent
agent=GovAgent(enable_audit=False)
cases=[
 {'name':'Arabic renewal intent','question':'أجدد الهوية الإماراتية','target':'renew'},
 {'name':'English replacement intent','question':'I lost my Emirates ID','target':'replace'},
 {'name':'First-issue intent','question':'Need ID for the first time','target':'new'},
]
passed=sum(agent.classify(c['question'])==c['target'] for c in cases)
s=agent.scenario(1)
observed=['TOO_EARLY' in [x['code'] for x in s['alerts']]]
s=agent.scenario(2,s['session_id']);observed.append('PASSPORT_TOO_SHORT' in [x['code'] for x in s['alerts']])
s=agent.scenario(3,s['session_id']);observed.append('PHOTO_MISSING' in [x['code'] for x in s['alerts']])
record={'type':'synthetic_in-repository evaluation','intent_classification':{'passed':passed,'total':len(cases)},'scenario_policy_gates':{'passed':sum(observed),'total':len(observed)},'kb_chunks':len(agent.kb.chunks),'note':'Small, curated synthetic tests only; not a real-world accuracy estimate.'}
(ROOT:=Path(__file__).resolve().parents[1]/'artifacts').mkdir(exist_ok=True)
(ROOT/'evaluation_results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
