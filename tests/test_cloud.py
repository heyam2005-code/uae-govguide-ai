"""Stage 3 tests use a fake API; no credentials or network needed."""
from types import SimpleNamespace
import json

import app.cloud as cloud
import app.dialogue as dialogue
from app.core import GovAgent


class FakeResponses:
    def __init__(self, output):
        self.output=output
        self.calls=[]
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output)


class FakeClient:
    def __init__(self, responses):
        self.responses=responses


def set_cloud(monkeypatch, explanations=True):
    monkeypatch.setenv('ENABLE_LLM','1')
    monkeypatch.setenv('ALLOW_CLOUD_NLU','1')
    monkeypatch.setenv('ALLOW_CLOUD_EXPLANATIONS','1' if explanations else '0')
    monkeypatch.setenv('OPENAI_API_KEY','demo-key-NEVER-A-REAL-KEY')


def test_cloud_disabled_by_default_does_not_invoke_api(monkeypatch):
    monkeypatch.setenv('ENABLE_LLM','0')
    monkeypatch.setenv('ALLOW_CLOUD_NLU','0')
    monkeypatch.setenv('OPENAI_API_KEY','')
    monkeypatch.setattr(cloud,'_client',lambda: (_ for _ in ()).throw(AssertionError('cloud called')))
    vals,mode=cloud.extract_slots('أريد تجديد الهوية',None)
    assert vals=={} and mode=='local'


def test_structured_slot_extraction_validates_response(monkeypatch):
    set_cloud(monkeypatch)
    res=FakeResponses(json.dumps({
        'service_id':'renew','category':'citizen','emirate':'Dubai','age':29,
        'expiry_months':2,'passport_valid_months':12,'has_photo':True,'urgent':True
    }))
    monkeypatch.setattr(cloud,'_client',lambda: FakeClient(res))
    values,mode=cloud.extract_slots('أريد تجديدًا عاجلًا، عمري 29، وباقي شهرين',None)
    assert mode=='cloud_nlu' and values['urgent'] and values['age']==29
    assert res.calls[0]['store'] is False
    assert res.calls[0]['text']['format']['type']=='json_schema'


def test_cloud_return_data_rejects_bad_values(monkeypatch):
    set_cloud(monkeypatch)
    data={'service_id':'fake','category':'unknown','emirate':'Mars','age':200,'expiry_months':999,
          'passport_valid_months':-999,'has_photo':'yes','urgent':1}
    monkeypatch.setattr(cloud,'_client',lambda: FakeClient(FakeResponses(json.dumps(data))))
    val,mode=cloud.extract_slots('any data',None)
    assert val=={} and mode=='cloud_nlu'


def test_api_error_reverts_to_local(monkeypatch):
    set_cloud(monkeypatch)
    monkeypatch.setattr(cloud,'_client',lambda: (_ for _ in ()).throw(ConnectionError('offline')))
    vals,mode=cloud.extract_slots('أريد تجديد هوية',None)
    assert vals=={} and mode=='fallback'


def test_deterministic_local_correction_overrides_cloud(monkeypatch):
    monkeypatch.setattr(dialogue,'extract_slots',lambda message,pending: ({'age':19},'cloud_nlu'))
    agent=dialogue.DialogueAgent(GovAgent(enable_audit=False))
    result=agent.respond('أنا مواطن إماراتي عمري 29 بدي أجدد هويتي عادي، باقي شهرين على الهوية وجوازي باقي 12 شهر وعندي صورة')
    assert result['profile']['age']==29
    assert result['stage']=='ready'


def test_pii_input_skips_cloud(monkeypatch):
    monkeypatch.setattr(dialogue,'extract_slots',lambda *args: (_ for _ in ()).throw(AssertionError('cloud called')))
    agent=dialogue.DialogueAgent(GovAgent(enable_audit=False))
    res=agent.respond('أريد تجديد هويتي ورقمها 784-1234-1234567-1')
    assert res['privacy_note'] and res['llm_mode']=='local'


def test_grounded_explanation_requires_sources(monkeypatch):
    set_cloud(monkeypatch)
    monkeypatch.setattr(cloud,'_client',lambda: (_ for _ in ()).throw(AssertionError('cloud called')))
    explanation,mode=cloud.explain_grounded('ليش؟',{'stage':'ready'},{'name_ar':'خدمة','name_en':'service'},[],'ar')
    assert explanation is None and mode=='local'


def test_ungrounded_number_rejected(monkeypatch):
    set_cloud(monkeypatch)
    res=FakeResponses('لازم تدفع 99999 درهم')
    monkeypatch.setattr(cloud,'_client',lambda: FakeClient(res))
    explanation,mode=cloud.explain_grounded('ليش لازم اروح؟',{
        'stage':'ready','fees':['AED 200'], 'route':'urgent_in_person','alerts':[],'steps':[]
    },{'name_ar':'تجديد الهوية','name_en':'renewal'},[{'text_ar':'الخدمة عاجلة حضورية','text_en':'In person','source_url':'https://icp.gov.ae'}],'ar')
    assert explanation is None and mode=='fallback'
    assert res.calls[0]['store'] is False


def test_explanation_shows_only_as_supplement(monkeypatch):
    set_cloud(monkeypatch)
    monkeypatch.setattr(dialogue,'extract_slots',lambda *args: ({},'local'))
    monkeypatch.setattr(dialogue,'explain_grounded',lambda *args: ('هذا شرح توضيحي من المصدر','cloud_explanation'))
    a=dialogue.DialogueAgent(GovAgent(enable_audit=False))
    result=a.respond('أنا مواطن إماراتي عمري 29 بدي أجدد هويتي عاجل باقي شهرين على الهوية وجوازي باقي 12 شهر وعندي صورة بدبي')
    r2=a.respond('ليش لازم اروح المركز؟',result['session_id'])
    assert r2['stage']=='ready'
    assert r2['route']=='urgent_in_person'
    assert 'الرسوم المنشورة' in r2['answer']
    assert 'شرح توضيحي' in r2['answer']
    assert r2['llm_mode']=='cloud_explanation'
