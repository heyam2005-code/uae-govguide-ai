import json
from pathlib import Path
import pytest
from app.core import GovAgent

@pytest.fixture
def agent():return GovAgent(enable_audit=False)

def profile(**kwargs):return {'category':'resident','expiry_months':2,'passport_valid_months':12,'age':29,'emirate':'Dubai','has_photo':True,**kwargs}

def test_arabic_and_english_classification(agent):
    assert agent.classify('بدي أجدد هويتي')=='renew'
    assert agent.classify('My Emirates ID has been lost')=='replace'
    assert agent.classify('First time issuing a new ID')=='new'

def test_unknown_service_requests_clarification(agent):
    out=agent.answer('مرحبا',profile=profile())
    assert out['stage']=='needs_service' and not out['service_id']

def test_renewal_early_block(agent):
    data=profile();data['expiry_months']=8
    out=agent.answer('تجديد الهوية',service_id='renew',profile=data)
    assert out['stage']=='needs_information'
    assert 'TOO_EARLY' in [x['code'] for x in out['alerts']]

def test_passport_validity_block(agent):
    data=profile();data['passport_valid_months']=2
    out=agent.answer('تجديد الهوية',service_id='renew',profile=data)
    assert 'PASSPORT_TOO_SHORT' in [x['code'] for x in out['alerts']]

def test_missing_photo_block(agent):
    data=profile();data['has_photo']=False
    out=agent.answer('تجديد الهوية',service_id='renew',profile=data)
    assert 'PHOTO_MISSING' in [x['code'] for x in out['alerts']]

def test_renewal_progress_when_ready(agent):
    x=agent.answer('تجديد',service_id='renew',profile=profile())
    y=agent.answer('أنجزت الخطوة',session_id=x['session_id'],profile=profile(),advance=True)
    assert x['stage']=='ready' and y['stage']=='in_progress'
    assert y['steps'][0]['done'] is True

def test_blocked_does_not_advance(agent):
    p=profile();p['passport_valid_months']=1
    x=agent.answer('تجديد',service_id='renew',profile=p)
    y=agent.answer('next',session_id=x['session_id'],profile=p,advance=True)
    assert y['steps'][0]['done'] is False

def test_replacement_fee_and_remaining_validity(agent):
    x=agent.answer('lost Emirates ID',service_id='replace',profile=profile())
    assert any('300' in x for x in x['fees'])
    assert 'icp_replace' in [s['id'] for s in x['sources']]

def test_only_eligible_verified_centres_in_emirate(agent):
    # New stage-4 safety constraint: resident renewals must not be sent to
    # Dubai ICP identity centres whose renewal is listed for citizen/GCC only.
    x=agent.answer('renew ID',service_id='renew',profile=profile())
    assert x['centres']==[]
    citizen=agent.answer('renew ID',service_id='renew',profile=profile(category='citizen'))
    assert citizen['centres']
    assert all(z['emirate']=='Dubai' for z in citizen['centres'])
    assert all(z['distance_km'] is None for z in citizen['centres'])

def test_scenario_released_sequentially(agent):
    out=agent.scenario(1)
    assert 'TOO_EARLY' in [x['code'] for x in out['alerts']]
    wrong=agent.scenario(3,out['session_id'])
    assert 'error' in wrong
    two=agent.scenario(2,out['session_id'])
    assert 'PASSPORT_TOO_SHORT' in [x['code'] for x in two['alerts']]
    three=agent.scenario(3,out['session_id'])
    assert 'PHOTO_MISSING' in [x['code'] for x in three['alerts']]

def test_kb_sources_traceable(agent):
    hits=agent.kb.search('Emirates ID renewal passport 3 months expiry',service_id='renew')
    assert hits and all(h['source_url'].startswith('https://') for h in hits)
    assert any(h['source_id']=='icp_renew' for h in hits)

def test_no_sensitive_user_message_in_audit(tmp_path,agent,monkeypatch):
    import app.core as core
    monkeypatch.setattr(core,'ROOT',tmp_path)
    a=GovAgent(enable_audit=True)
    msg='renew Emirates ID 784-1234-1234567-1 personal name'
    a.answer(msg,service_id='renew',profile=profile())
    data=(tmp_path/'artifacts'/'audit_log.jsonl').read_text()
    assert '784-1234-1234567-1' not in data and 'personal name' not in data
    assert 'policy_flags' in data


def test_urgent_renewal_uses_in_person_steps_and_advice(agent):
    p={'category':'citizen','expiry_months':2,'passport_valid_months':12,
       'age':29,'emirate':'Dubai','has_photo':True,'urgent':True}
    result=agent.answer('أجدد هويتي بسرعة',service_id='renew',profile=p)
    assert result['route']=='urgent_in_person'
    assert 'URGENT_IN_PERSON' in [a['code'] for a in result['alerts']]
    assert 'موظف' in result['steps'][0]['ar']
    assert 'بوابة الخدمات الذكية' not in result['steps'][0]['ar']
    assert 'ابدأ المعاملة الفعلية من بوابة' not in result['answer']
    assert 'عاجل — الحضور' in result['answer']
    assert 'route' in [x.get('event') for x in result['trace']]


def test_standard_renewal_keeps_digital_steps(agent):
    p={'category':'citizen','expiry_months':2,'passport_valid_months':12,
       'age':29,'emirate':'Dubai','has_photo':True,'urgent':False}
    result=agent.answer('تجديد',service_id='renew',profile=p)
    assert result['route']=='standard_digital'
    assert 'بوابة الخدمات الذكية' in result['steps'][0]['ar']


def test_switching_route_resets_progress(agent):
    p={'category':'citizen','expiry_months':2,'passport_valid_months':12,
       'age':29,'emirate':'Dubai','has_photo':True,'urgent':False}
    start=agent.answer('تجديد',service_id='renew',profile=p)
    progressed=agent.answer('تم',session_id=start['session_id'],profile=p,advance=True)
    assert progressed['steps'][0]['done']
    switched=agent.answer('أريد الخدمة العاجلة',session_id=start['session_id'],profile={**p,'urgent':True})
    assert switched['route']=='urgent_in_person'
    assert switched['steps'][0]['current'] and not switched['steps'][0]['done']
    assert any(x.get('event')=='route-changed' for x in switched['trace'])


def test_blocked_urgent_never_advances(agent):
    p={'category':'resident','expiry_months':8,'passport_valid_months':12,
       'age':29,'emirate':'Dubai','has_photo':True,'urgent':True}
    result=agent.answer('تجديد عاجل',service_id='renew',profile=p,advance=True)
    assert result['stage']=='needs_information'
    assert result['route']=='urgent_in_person'
    assert result['steps'][0]['current']
    assert 'لا يمكن تأكيد جاهزية' in result['answer']


def test_other_urgent_services_have_in_person_route(agent):
    p={'category':'citizen','age':29,'emirate':'Dubai','has_photo':True,'urgent':True}
    for service_id in ('replace','new'):
        result=agent.answer('أحتاج الخدمة عاجل',service_id=service_id,profile=p)
        assert result['route']=='urgent_in_person'
        assert 'مركز ICP' in result['steps'][0]['ar']
