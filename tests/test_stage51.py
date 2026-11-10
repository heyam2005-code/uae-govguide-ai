"""Regression tests for centre recommendation continuity in conversational guidance."""
from app.core import GovAgent
from app.dialogue import DialogueAgent
from app.centre_guidance import DIRECTORY


def agent():
    return DialogueAgent(GovAgent(enable_audit=False))


def sequence(dialogue, messages):
    sid = None
    results = []
    for message in messages:
        result = dialogue.respond(message, sid)
        sid = result['session_id']
        results.append(result)
    return results


def test_full_user_scenario_keeps_neighbourhood_in_final_answer():
    results = sequence(agent(), [
        'أنا مواطن إماراتي، في دبي بمنطقة البرشاء، وبدي أجدد هويتي. وين أراجع وشو الإجراءات المطلوبة؟',
        '29 سنة', 'شهر', '12', 'نعم', 'عاجلة',
    ])
    r = results[-1]
    assert r['stage'] == 'ready'
    assert r['profile']['area'] == 'Al Barsha 3'
    assert r['route'] == 'urgent_in_person'
    assert r['centre_search']['centres'][0]['id'] == 'DXB-BARSHA'
    assert 'مركز البرشاء لإسعاد المتعاملين' in r['answer']
    assert 'لأن اسم منطقته يطابق المنطقة' in r['answer']
    assert 'ليس بحسب المسافة الفعلية' in r['answer']
    assert 'التأكد تحديدًا من استقبال طلبات الخدمة العاجلة' in r['answer']
    assert 'customer-happiness-center-al-barsha/' in r['answer']
    assert any(x['event'] == 'centre-context-recheck' and x['candidate_id']=='DXB-BARSHA'
               for x in r['trace'])
    assert any(x['url'].endswith('/customer-happiness-center-al-barsha/') for x in r['sources'])


def test_no_centre_claim_if_only_general_query():
    r = sequence(agent(), ['بدي اجدد هويتي', 'مواطن إماراتي', '29', 'شهرين', '12', 'نعم', 'عادي'])[-1]
    assert r['stage'] == 'ready'
    assert 'المركز المرشّح' not in r['answer']


def test_blocked_profile_with_location_does_not_encourage_visit():
    r = agent().respond('أنا مواطن إماراتي عمري 29 في دبي البرشاء وبدي أجدد عاجل، '
                        'هويتي باقي شهر وجوازي باقي شهر وعندي صورة، وين أراجع؟')
    assert r['stage'] == 'needs_information'
    assert 'المركز المرشّح' in r['answer']
    assert 'لا تتوجّه لتقديم الطلب قبل معالجة الملاحظات المانعة' in r['answer']


def test_resident_does_not_get_citizen_only_centre_when_context_rechecked():
    a = agent()
    r = a.respond('أنا مواطن إماراتي في دبي البرشاء، بدي أجدد الهوية، وين أراجع؟')
    assert r['centre_search']['centres']
    r = a.respond('أنا مقيم', r['session_id'])
    assert r['centre_search']['centres'] == []
    r = a.respond('29 سنة', r['session_id'])
    r = a.respond('شهر', r['session_id'])
    r = a.respond('12', r['session_id'])
    r = a.respond('نعم', r['session_id'])
    r = a.respond('عادية', r['session_id'])
    assert r['stage'] == 'ready'
    assert r['centre_search']['centres'] == []
    assert 'لم نجد مركزًا مطابقًا موثّقًا' in r['answer']
    assert DIRECTORY in r['answer']
    assert 'مركز البرشاء لإسعاد المتعاملين' not in r['answer']


def test_changed_emirate_clears_stale_area_and_rechecks_centre():
    a = agent()
    r = a.respond('أنا مواطن اماراتي دبي البرشاء بدي أجدد هويتي، وين أراجع؟')
    assert r['profile']['area'] == 'Al Barsha 3'
    r = a.respond('رح أقدم في أبوظبي', r['session_id'])
    assert r['profile']['emirate'] == 'Abu Dhabi'
    assert 'area' not in r['profile']
    assert all(c['emirate'] == 'Abu Dhabi' for c in r['centre_search']['centres'])


def test_service_change_discards_old_centre_request():
    a = agent()
    r = a.respond('أنا مواطن اماراتي بدبي البرشاء بدي أجدد الهوية، وين أراجع؟')
    r = a.respond('بل بدي بدل فاقد', r['session_id'])
    assert r['service_id'] == 'replace'
    assert not a.sessions[r['session_id']]['centre_requested']


def test_reset_clears_centre_context():
    a = agent()
    r = a.respond('أنا مواطن إماراتي دبي البرشاء بدي تجديد الهوية وين أراجع؟')
    a.reset(r['session_id'])
    r2 = a.respond('بدي اجدد هويتي')
    assert 'area' not in r2['profile']
    assert not a.sessions[r2['session_id']]['centre_requested']
