"""Regression cases based on official ICP card; synthetic data only."""
from app.dialogue import DialogueAgent
from app.core import GovAgent


def agent():
    return DialogueAgent(GovAgent(enable_audit=False))


def test_questions_answered_before_missing_slots():
    a=agent()
    result=a.respond('أنا مواطن إماراتي عمري 29 بدي أجدد هويتي بشكل عاجل. ليش لازم أزور مركز ICP بدل ما أقدم إلكترونيًا؟')
    assert result['stage']=='collecting'
    assert result['next_question'] is not None
    assert 'تنص بطاقة خدمة ICP' in result['answer']
    assert 'icp.gov.ae/services-details/' in result['answer']
    assert 'كم شهر باقي على انتهاء الهوية' in result['answer']


def test_combined_option_for_citizen_short_passport():
    a=agent()
    msgs=['أنا مواطن إماراتي عمري 29 بدي تجديد الهوية عاجل', 'شهرين','شهر','نعم','دبي']
    r=None;sid=None
    for m in msgs:
        r=a.respond(m,sid);sid=r['session_id']
    assert r['stage']=='needs_information'
    codes={x['code'] for x in r['alerts']}
    assert {'PASSPORT_TOO_SHORT','COMBINED_RENEWAL_OPTION'} <= codes
    assert 'تجديد الهوية وجواز السفر معًا' in r['answer']
    assert 'بديل مقترح' in r['answer']


def test_resident_not_given_citizen_combined_recommendation():
    a=agent()
    r=a.respond('أنا مقيم في دبي عمري 29 بدي أجدد الهوية عادي، باقي شهرين على الهوية والجواز باقي شهر وعندي صورة')
    assert r['stage']=='needs_information'
    assert 'PASSPORT_TOO_SHORT' in {x['code'] for x in r['alerts']}
    assert 'COMBINED_RENEWAL_OPTION' not in {x['code'] for x in r['alerts']}


def test_normal_renewal_does_not_claim_urgent_visit():
    a=agent()
    r=a.respond('أنا مواطن إماراتي عمري 29 بدي أجدد هويتي عادي، لماذا لا أقدم إلكترونيًا؟')
    assert 'تنص بطاقة خدمة ICP على البدء بزيارة' not in r['answer']
