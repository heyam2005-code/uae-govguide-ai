"""Stage 2 conversation regressions; only synthetic non-identifying profiles."""
from fastapi.testclient import TestClient
from app.main import app
from app.dialogue import DialogueAgent, _contextual_value
from app.core import GovAgent


def agent():
    return DialogueAgent(GovAgent(enable_audit=False))


def exchange(agent, messages):
    sid = None
    out = []
    for message in messages:
        result = agent.respond(message, sid)
        sid = result['session_id']
        out.append(result)
    return out


def test_chat_starts_with_a_clear_question():
    a = agent()
    r = a.respond('مرحبا')
    assert r['stage'] == 'needs_service'
    assert r['next_question'] and r['quick_replies']


def test_full_urgent_citizen_dialogue_goes_ready():
    a = agent()
    msgs = ['بدي أجدد هويتي بشكل عاجل', 'مواطن إماراتي', '29', 'شهرين', '12 شهر', 'نعم', 'دبي']
    results = exchange(a, msgs)
    assert results[0]['next_question'].startswith('إنت مواطن')
    assert results[-1]['stage'] == 'ready'
    assert results[-1]['route'] == 'urgent_in_person'
    assert results[-1]['profile']['expiry_months'] == 2
    assert results[-1]['steps'][0]['current']
    assert 'مركز ICP' in results[-1]['steps'][0]['ar']
    assert 'صورة شخصية' in results[-1]['answer']
    assert 'درهم' in results[-1]['answer']
    assert any(x['url'].startswith('https://icp.gov.ae/') for x in results[-1]['sources'])


def test_long_single_turn_extracts_durations_without_confusing_age():
    a = agent()
    r = a.respond('بدي أجدد هويتي عاجل، أنا مواطن إماراتي، عمري 29، هويتي باقي شهرين وجوازي باقي 12 شهر وعندي صورة بدبي')
    assert r['stage'] == 'ready'
    assert r['profile']['age'] == 29
    assert r['profile']['expiry_months'] == 2
    assert r['profile']['passport_valid_months'] == 12
    assert r['profile']['emirate'] == 'Dubai'


def test_durations_in_reverse_order():
    result = _contextual_value('جوازي باقي 12 شهر والهوية باقي شهرين', None)
    assert result['passport_valid_months'] == 12
    assert result['expiry_months'] == 2


def test_reject_early_renewal_and_keep_source():
    a = agent()
    r = a.respond('أنا مقيم في دبي وعمري 29 بدي أجدد هويتي العادية، باقي 8 شهور على الهوية وجوازي باقي 12 شهر وعندي صورة')
    assert r['stage'] == 'needs_information'
    assert 'TOO_EARLY' in [x['code'] for x in r['alerts']]
    assert any(x['id'] == 'icp_renew' for x in r['sources'])


def test_no_photo_blocks_until_user_changes_answer():
    a = agent()
    r = a.respond('أنا مواطن إماراتي  عمري 29 بدي أجدد هويتي عادي، باقي شهرين على الهوية وجوازي باقي 12 شهر وما عندي صورة')
    assert r['stage'] == 'needs_information'
    assert 'PHOTO_MISSING' in [x['code'] for x in r['alerts']]
    r2 = a.respond('هسا معي صورة حديثة',r['session_id'])
    assert r2['stage'] == 'ready'
    assert 'PHOTO_MISSING' not in [x['code'] for x in r2['alerts']]


def test_user_says_no_only_for_pending_boolean():
    a = agent()
    out = exchange(a, ['بدل فاقد', 'مقيم', '29', 'لا', 'عادية'])
    assert out[-1]['stage']=='needs_information'
    assert out[-1]['profile']['has_photo'] is False
    assert out[-1]['profile']['urgent'] is False


def test_change_route_resets_step_progress():
    a = agent()
    r = a.respond('بدي أجدد الهوية، أنا مواطن إماراتي عمري 29 هويتي باقي شهرين والجواز باقي 12 شهر وعندي صورة، عادي')
    assert r['stage'] == 'ready'
    r = a.respond('أنجزت الخطوة',r['session_id'])
    assert r['stage']=='in_progress'
    r = a.respond('بدي خدمة عاجلة',r['session_id'])
    assert r['stage']=='collecting' and r['next_question']
    r = a.respond('دبي',r['session_id'])
    assert r['route']=='urgent_in_person'
    assert r['steps'][0]['current'] is True and r['steps'][0]['done'] is False


def test_english_conversation():
    a = agent()
    res = exchange(a,['I need to renew my Emirates ID','UAE citizen','age 29','2 months','12 months','yes','standard'])
    assert res[-1]['stage']=='ready'
    assert 'Next step:' in res[-1]['answer']
    assert res[-1]['route']=='standard_digital'


def test_profile_data_is_session_isolated():
    a = agent()
    first = a.respond('UAE citizen renewal urgent')
    other = a.respond('lost ID')
    assert 'category' not in other['profile']
    assert first['session_id']!=other['session_id']


def test_reset_clears_dialogue_and_underlying_progress():
    a=agent()
    r=a.respond('أريد تجديد الهوية')
    sid=r['session_id']
    assert sid in a.sessions
    a.reset(sid)
    assert sid not in a.sessions and sid not in a.gov.sessions


def test_pii_is_not_in_audit_or_source_message(tmp_path,monkeypatch):
    import app.core as core
    monkeypatch.setattr(core, 'ROOT', tmp_path)
    a = DialogueAgent(GovAgent(enable_audit=True))
    identifier='784-1234-1234567-1'
    r=a.respond('أجدد هويتي ورقمها '+identifier)
    assert r['privacy_note']
    log=(tmp_path/'artifacts'/'audit_log.jsonl').read_text()
    assert identifier not in log


def test_api_page_and_conversation_endpoints():
    with TestClient(app) as client:
        page=client.get('/assistant')
        assert page.status_code==200 and 'UAE GovGuide AI' in page.text
        r=client.post('/api/assistant',json={'message':'بدي تجديد الهوية'})
        assert r.status_code==200
        payload=r.json()
        assert payload['session_id'] and payload['next_question']
        c=client.post('/api/assistant/reset',json={'session_id':payload['session_id']})
        assert c.status_code==200 and c.json()['status']=='reset'
