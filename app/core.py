"""Stateful, source-grounded service navigator.
The deterministic reasoning layer is runnable without cloud credentials.
Optional LLM only paraphrases a decision that was already made by the policy engine.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import csv, json, os, re, uuid
from collections import defaultdict
from typing import Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.locator import CentreLocator

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def load_json(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def new_session():return str(uuid.uuid4())

def _normalize(s: str) -> str:
    s=s.lower().strip().replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه').replace('ى','ي')
    return re.sub(r'\s+',' ',s)

class KnowledgeBase:
    def __init__(self):
        self.chunks=[json.loads(line) for line in (DATA/'kb.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        self.vectorizer=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True,min_df=1)
        docs=[_normalize(c['title']+' '+c['text_en']+' '+c['text_ar']) for c in self.chunks]
        self.matrix=self.vectorizer.fit_transform(docs)
    def search(self,query:str,service_id:str|None=None,limit:int=5):
        q=self.vectorizer.transform([_normalize(query)])
        scores=cosine_similarity(q,self.matrix).ravel()
        ranked=sorted(enumerate(scores),key=lambda it:it[1],reverse=True)
        results=[]
        for idx,score in ranked:
            c=self.chunks[idx]
            if service_id and c['service_id'] not in (None,service_id):continue
            if score <= 0: continue
            results.append({**c,'score':round(float(score),3)})
            if len(results)>=limit:break
        return results

class GovAgent:
    def __init__(self, enable_audit:bool=True):
        self.services={s['id']:s for s in load_json('services.json')}
        self.sources={s['id']:s for s in load_json('sources.json')}
        self.policies=load_json('policies.json')
        self.gap_hypotheses=json.loads((DATA.parent/'docs'/'policy_gap_hypotheses.json').read_text(encoding='utf-8'))
        self.kb=KnowledgeBase()
        with (DATA/'centres.csv').open(encoding='utf-8-sig',newline='') as f:self.centres=list(csv.DictReader(f))
        self.locator=CentreLocator()
        self.sessions={}
        self.enable_audit=enable_audit

    def classify(self,message:str)->str|None:
        text=_normalize(message)
        hits={}
        for sid,s in self.services.items():
            score=0
            for word in s['keywords']:
                w=_normalize(word)
                if (w.isascii() and re.search(r'\b'+re.escape(w)+r'\b',text)) or (not w.isascii() and w in text):
                    score+=2 if len(w)>=5 else 1
            hits[sid]=score
        best=max(hits,key=hits.get)
        if hits[best]<1:return None
        contenders=[k for k,v in hits.items() if v==hits[best]]
        if len(contenders)>1 or sum(v>0 for v in hits.values())>1:return 'ambiguous'
        return best

    def _state(self,sid:str):
        if sid not in self.sessions:self.sessions[sid]={'service_id':None,'progress':0,'scenario':0}
        return self.sessions[sid]

    def _check(self,service,profile:dict)->tuple[list[dict],list[dict]]:
        alerts=[];trace=[]
        typ=profile.get('category','unknown')
        age=profile.get('age')
        expiry=profile.get('expiry_months')
        passport=profile.get('passport_valid_months')
        urgent=profile.get('urgent',False)
        if typ=='unknown':
            alerts.append({'severity':'info','code':'CATEGORY_REQUIRED','message':'يرجى تحديد صفتك (مواطن/مقيم/مواطن خليجي) لتحديد الشروط والرسوم بدقة.','blocking':True})
        if service['id']=='renew':
            if expiry is None: alerts.append({'severity':'info','code':'EXPIRY_REQUIRED','message':'حدّد عدد الأشهر المتبقية لانتهاء الهوية؛ يمكن إدخال قيمة سالبة للهوية المنتهية.','blocking':True})
            elif typ!='unknown':
                cutoff=12 if typ=='citizen' else 6
                if expiry>=cutoff:
                    alerts.append({'severity':'warning','code':'TOO_EARLY','message':f'موعد التجديد لم يحن وفق نافذة الهيئة لهذه الفئة: أقل من {cutoff} أشهر قبل الانتهاء، أو بعد الانتهاء.','blocking':True})
            if passport is None:
                alerts.append({'severity':'info','code':'PASSPORT_VALIDITY_UNKNOWN','message':'تأكّد من صلاحية الجواز؛ تشير الهيئة إلى اشتراط 3 أشهر على الأقل للتجديد.','blocking':False})
            elif passport<3:
                alerts.append({'severity':'warning','code':'PASSPORT_TOO_SHORT','message':'صلاحية الجواز أقل من 3 أشهر؛ لا يمكن تأكيد أهلية تجديد الهوية منفردة وفق بطاقة ICP الرسمية.','blocking':True})
                # The official identity-renewal card directs customers whose
                # ID and passport are both due to the combined renewal service.
                # This is an OPTION to verify, not an automatic eligibility approval.
                if typ=='citizen' and expiry is not None and expiry<12:
                    alerts.append({'severity':'info','code':'COMBINED_RENEWAL_OPTION',
                                   'message':'للمواطن الإماراتي: عندما تكون الهوية والجواز كلاهما مستحقين للتجديد، تشير ICP إلى استخدام خدمة «تجديد الهوية وجواز السفر معًا». تحقق من توفرها وشروطها عبر الهيئة قبل أي دفع أو زيارة.',
                                   'blocking':False})
        if service['id']=='new' and passport is not None and passport<3 and typ!='citizen':
            alerts.append({'severity':'warning','code':'PASSPORT_TOO_SHORT','message':'قد لا يستوفي الجواز شرط الصلاحية المطلوب للإصدار الأول؛ راجع الهيئة.','blocking':True})
        if profile.get('has_photo') is False and service['eligibility'].get('requires_fresh_photo'):
            alerts.append({'severity':'warning','code':'PHOTO_MISSING','message':'الصورة الشخصية مطلوبة لهذه الخدمة وفق الفئة؛ جهّز صورة حديثة قبل التقديم.','blocking':True})
        if age is not None and age>=15:
            alerts.append({'severity':'info','code':'BIOMETRICS_REQUIRED','message':'من أتم 15 عامًا تُطلب منه إجراءات البصمة والتوقيع في مركز الهيئة وفق تعليمات الخدمة.','blocking':False})
        if urgent:
            alerts.append({'severity':'info','code':'URGENT_IN_PERSON','message':'الخدمة العاجلة تبدأ بزيارة مركز الهيئة، وليست معاملة إلكترونية بالكامل.','blocking':False})
        if service['id']=='renew' and typ=='resident':
            msg=('تحقق من مسار تجديد الإقامة المرتبط بالهوية؛ تختلف آلية الربط في دبي عن باقي الإمارات وفق بطاقة خدمة الهيئة.')
            alerts.append({'severity':'info','code':'RESIDENCE_DEPENDENCY','message':msg,'blocking':False})
        trace.append({'check':'eligibility-and-dependencies','result':'blocked' if any(a['blocking'] for a in alerts) else 'provisionally-ready','factors':['category','expiry_window','passport_validity','document_readiness','biometrics','urgent']})
        return alerts,trace

    def _fees(self,service,profile):
        fees=service['fees'];cat=profile.get('category','unknown');age=profile.get('age')
        out=[]
        if cat=='citizen':
            if age is not None:out.append(fees['citizen_under_21'] if age<21 else fees['citizen_21_plus']) if 'citizen_under_21' in fees else None
            elif 'citizen_under_21' in fees:out += [fees['citizen_under_21'],fees['citizen_21_plus']]
        if cat=='resident' and 'resident' in fees:out.append(fees['resident'])
        if cat=='gcc' and 'gcc' in fees:out.append(fees['gcc'])
        if service['id']=='replace':out += [fees['replacement'],fees['smart']]
        if profile.get('urgent') and 'urgent' in fees:out.append(fees['urgent'])
        if not out:out=['تعتمد الرسوم على الفئة والعمر ونوع الطلب؛ راجع بطاقة الخدمة وشاشة الدفع الرسمية.']
        return out

    def _centres(self,emirate:str|None,service_id:str|None=None,category:str='unknown',urgent:bool=False,area:str|None=None):
        if not emirate or not service_id or category=='unknown':return []
        return self.locator.recommend(emirate,service_id,category,urgent=urgent,area=area)['centres']

    def _route_steps(self,service:dict,profile:dict)->tuple[str,list[dict]]:
        """Choose the *full* procedure before marking progress or composing advice.

        ICP renewal guidance says urgent requests start in person through an ICP
        service officer. The published urgent centre rule also covers identity
        issuance and replacement; never infer centre eligibility from emirate
        alone. A user must verify the particular centre and applicant category.
        """
        if not profile.get('urgent',False):
            return 'standard_digital',service['steps']
        label=service['name_ar']
        return 'urgent_in_person',[
            {'ar':f'تحقق من مركز ICP الذي يقدّم «{label}» العاجلة لفئتك وأوقات عمله، ثم توجّه إليه لبدء الطلب لدى موظف الخدمة.',
             'en':'Confirm that a suitable ICP centre offers the urgent service for your applicant category, check its hours, and visit to start the application with a service officer.'},
            {'ar':'قدّم طلب الخدمة العاجلة مباشرة إلى موظف المركز، مع توضيح فئة مقدم الطلب وحالته.',
             'en':'Start the urgent application with the ICP centre service officer and confirm your applicant category.'},
            {'ar':'راجع بيانات الطلب مع الموظف، وقدّم المستندات والصورة الحديثة المطلوبة حسب فئتك.',
             'en':'Review the application information and supply documents and a recent photo as applicable.'},
            {'ar':'سدّد الرسوم التي يحددها موظف المركز بعد تأكيد الأهلية، بما فيها رسوم الخدمة العاجلة إن انطبقت.',
             'en':'Pay the confirmed fees at the ICP centre, including any eligible urgent-service surcharge.'},
            {'ar':'أكمل إجراءات البصمة والتوقيع في المركز إذا كانت مطلوبة لحالتك.',
             'en':'Complete fingerprints and signature at the centre if your case requires them.'},
            {'ar':'تابع حالة الطلب واستلم البطاقة العاجلة من مركز الهيئة عندما تصبح جاهزة وفق تعليمات المركز.',
             'en':'Track the application and collect the urgent card at the ICP centre when ready, following centre instructions.'},
        ]

    @staticmethod
    def _safe_message(message):
        # Do not send identifier-like numbers to third-party model or audit files.
        return re.sub(r'(?<!\d)(?:\d[\s-]?){9,18}(?!\d)','[REDACTED_IDENTIFIER]',message)[:600]

    def _optional_llm(self,draft:str,query:str,passages:list[dict]):
        if os.getenv('ENABLE_LLM','0') !='1' or not os.getenv('OPENAI_API_KEY'):return draft,False
        try:
            from openai import OpenAI
            context='\n'.join(f"[{p['id']}] {p['text_en'][:380]} (source: {p['source_url']})" for p in passages)
            response=OpenAI(timeout=12).responses.create(
                model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
                instructions='Rewrite the pre-approved Arabic response clearly. Never change facts, status, fees, sources, or policy determinations. Use only the supplied context; no speculative rules; do not ask for personal identifier data. Max 180 words.',
                input=f'Approved answer:\n{draft}\nQuestion:\n{self._safe_message(query)}\nRetrieved evidence:\n{context}'
            )
            refined=(response.output_text or '').strip()
            return (refined if refined else draft),bool(refined)
        except Exception:
            return draft,False

    def answer(self,message:str,session_id:str|None=None,service_id:str|None=None,profile:dict|None=None,advance:bool=False):
        sid=session_id or new_session(); state=self._state(sid)
        profile=profile or {}
        if service_id and service_id in self.services:state['service_id']=service_id;state['progress']=0 if state.get('last_service')!=service_id else state['progress']
        elif not state['service_id']:
            guess=self.classify(message)
            if guess in self.services:state['service_id']=guess
        s=self.services.get(state['service_id'])
        if not s:
            query=message or 'Emirates ID'
            retrieval=self.kb.search(query,limit=4)
            reply=('خلّينا نبدأ بتحديد نوع المعاملة: تجديد الهوية، بدل فاقد/تالف، أو إصدار لأول مرة. لا تدخل رقم الهوية أو الجواز.' if self.classify(query)!='ambiguous' else 'وجدت أكثر من خدمة محتملة. اختَر نوع المعاملة من القائمة لتجنّب التوجيه الخاطئ.')
            return dict(session_id=sid,service_id=None,answer=reply,stage='needs_service',steps=[],alerts=[],fees=[],centres=[],sources=[],retrieved=[{'id':x['id'],'score':x['score']} for x in retrieval],trace=[{'event':'service-classification','outcome':'clarification-required'}],llm_used=False)
        alerts,trace=self._check(s,profile)
        route,route_steps=self._route_steps(s,profile)
        # A change of submission channel invalidates progress on the prior route.
        # Without this, switching from digital to urgent could mark an in-person
        # task as done even though the user only completed an online step.
        previous_route=state.get('route')
        if previous_route and previous_route!=route:
            state['progress']=0
            # An advance click cannot complete a step on a newly chosen route.
            advance=False
            trace.append({'event':'route-changed','from':previous_route,'to':route,'outcome':'progress-reset'})
        state['route']=route
        blocked=any(x['blocking'] for x in alerts)
        if advance and not blocked:state['progress']=min(state['progress']+1,len(route_steps))
        elif advance and blocked: trace.append({'event':'progress-advance','outcome':'denied-policy-block'})
        state['last_service']=s['id']
        progress=state['progress'];stage='needs_information' if blocked else 'ready' if progress==0 else 'in_progress' if progress<len(route_steps) else 'locally_completed'
        docs=s['documents'].get(profile.get('category','unknown'),[])
        if not docs:docs=['تختلف المستندات حسب فئتك؛ يجب مراجعة بطاقة الخدمة الرسمية.']
        fees=self._fees(s,profile)
        focus=message.strip() or s['name_en']
        retrieved=self.kb.search(focus+' '+s['name_en'],service_id=s['id'],limit=5)
        primary=self.sources[s['source_id']]
        src_ids=[s['source_id'],'uaepass','uae_pdpl']
        centres=self._centres(profile.get('emirate'),s['id'],profile.get('category','unknown'),profile.get('urgent',False),profile.get('area'))
        if centres:
            src_ids.append('icp_centers')
            src_ids.extend('center_'+c['id'].lower().replace('-','_') for c in centres[:4])
        if any(a['code'].startswith('PASSPORT') for a in alerts):src_ids.append(s['source_id'])
        src_ids=list(dict.fromkeys(src_ids))
        gap_ids=[]
        if s['id']=='renew' and profile.get('category')=='resident':gap_ids.append('GAP-01')
        if any(a['code'] in ('CATEGORY_REQUIRED','PHOTO_MISSING') for a in alerts):gap_ids.append('GAP-02')
        if centres:gap_ids.append('GAP-03')
        gap_ids.append('GAP-04')
        current_gaps=[{**g,'evidence_urls':[self.sources[src]['url'] for src in g['evidence_source_ids'] if src in self.sources]} for g in self.gap_hypotheses if g['id'] in gap_ids]
        steptext=route_steps[progress]['ar'] if progress<len(route_steps) else 'اكتملت خطوات العرض المحلي؛ استكمل الإجراء الفعلي لدى الجهة الحكومية المختصة.'
        route_label='عاجل — الحضور إلى مركز ICP' if route=='urgent_in_person' else 'عادي — القنوات الرقمية المعتمدة'
        lines=[f'الخدمة: {s["name_ar"]} — الجهة: ICP.', f'المسار المختار: {route_label}.', f'المستندات بحسب الفئة: {"؛ ".join(docs)}.', f'الرسوم المنشورة بحسب المعلومات المدخلة: {"؛ ".join(fees)}.']
        if alerts:lines.append('ملاحظات التحقق: '+'؛ '.join(a['message'] for a in alerts))
        lines.append(('لا يمكن تأكيد جاهزية الطلب بعد؛ عالج التنبيهات المانعة أولًا.' if blocked else f'الخطوة التالية ({min(progress+1,len(route_steps))}/{len(route_steps)}): {steptext}'))
        if route=='urgent_in_person':
            lines.append('ابدأ المعاملة العاجلة فعليًا لدى موظف مركز ICP الذي يؤكد تقديم الخدمة لفئتك. لا يقدّم هذا التطبيق الطلب نيابةً عنك.')
        else:
            lines.append('ابدأ المعاملة الفعلية من بوابة ICP الرسمية باستخدام UAE PASS. التطبيق لا يقدّم الطلب نيابةً عنك.')
        lines.append('المعلومات مرجعية، وقد تختلف المتطلبات باختلاف الفئة والطلب. تأكد من بطاقة الخدمة قبل الدفع أو الزيارة.')
        reply='\n\n'.join(lines)
        reply,llm_used=self._optional_llm(reply,message,retrieved)
        trace=[{'event':'service-classification','outcome':s['id'],'source_id':s['source_id']},
               {'event':'retrieval','outcome':[r['id'] for r in retrieved],'scores':[r['score'] for r in retrieved]},*trace,
               {'event':'route','outcome':'hold_for_eligibility_review' if blocked else route,'selected_route':route,'progress_step':progress,'basis_source_id':s['source_id']},
               {'event':'source-attribution','outcome':src_ids},
               {'event':'policy-gap-hypotheses','outcome':gap_ids,'disclaimer':'Research hypotheses, not legal violations'}]
        result=dict(session_id=sid,service_id=s['id'],route=route,answer=reply,stage=stage,steps=[{**st,'index':i+1,'done':i<progress,'current':i==progress} for i,st in enumerate(route_steps)],alerts=alerts,fees=fees,centres=centres,official_portal=s['official_portal'],sources=[{'id':id,'title':self.sources[id]['title'],'url':self.sources[id]['url']} for id in src_ids],retrieved=[{'id':r['id'],'title':r['title'],'score':r['score'],'source_url':r['source_url']} for r in retrieved],trace=trace,llm_used=llm_used,policy_gap_hypotheses=current_gaps)
        if self.enable_audit:self._audit(sid,s['id'],stage,trace,alerts,profile)
        return result

    def _audit(self,sid,service,stage,trace,alerts,profile):
        # NO user text, user names, document numbers or raw profile values.
        row=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),session_id=sid,service=service,stage=stage,policy_flags=[x['code'] for x in alerts],decisions=trace,source_ids=[x.get('source_id') for x in trace if x.get('source_id')],profile_fields_supplied=sorted(profile.keys()))
        path=ROOT/'artifacts'/'audit_log.jsonl';path.parent.mkdir(exist_ok=True)
        with path.open('a',encoding='utf-8') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n')

    def scenario(self,step:int,session_id:str|None=None):
        """Release sequential hypothetical events; explicit structured evaluation case."""
        sid=session_id or new_session();state=self._state(sid)
        if step!=state.get('scenario',0)+1:
            return {'error':'Scenario events must be released in order (1, then 2, then 3).','next_expected':state.get('scenario',0)+1}
        events={
            1:{'name':'Resident applies too early','event':'A UAE resident requests renewal with 8 months left on their card.','profile':{'category':'resident','expiry_months':8,'passport_valid_months':12,'age':29,'emirate':'Dubai','has_photo':True}},
            2:{'name':'New timing data and passport obstacle','event':'Update: only 2 months remain until ID expiry, but the passport expires in 2 months.','profile':{'category':'resident','expiry_months':2,'passport_valid_months':2,'age':29,'emirate':'Dubai','has_photo':True}},
            3:{'name':'Passport updated; photo missing','event':'Update: passport now has 18 months validity, but the applicant has no fresh personal photo.','profile':{'category':'resident','expiry_months':2,'passport_valid_months':18,'age':29,'emirate':'Dubai','has_photo':False}},
        }
        ev=events[step];state['scenario']=step;state['service_id']='renew';state['progress']=0
        r=self.answer(ev['event'],session_id=sid,service_id='renew',profile=ev['profile'])
        r.update(scenario_event=ev['name'],scenario_description=ev['event'],scenario_step=step)
        return r
