"""Scenario-based, reproducible offline tests of dialogue + service matching."""
from fastapi.testclient import TestClient
from app.core import GovAgent
from app.dialogue import DialogueAgent
from app.centre_guidance import is_centre_question, detect_area
from app.main import app


def new_agent():return DialogueAgent(GovAgent(enable_audit=False))


def test_area_recognition_is_grounded():
    assert detect_area('أنا ساكنة في البرشاء')=='Al Barsha 3'
    assert detect_area('في دبي') is None
    assert detect_area('المنطقة ما حددتها') is None


def test_centre_intent_not_confused_with_why_question():
    assert is_centre_question('وين أراجع؟')
    assert is_centre_question('which ICP center should I choose?')
    assert not is_centre_question('ليش لازم أزور مركز ICP بدل ما أقدم اونلاين؟')


def test_citizen_asks_where_and_area_ranks_correctly_without_fabricated_distance():
    r=new_agent().respond('أنا مواطن إماراتي في دبي البرشاء وبدي أجدد الهوية، وين أراجع؟')
    assert r['stage']=='collecting'
    assert r['centre_search']['centres'][0]['id']=='DXB-BARSHA'
    assert r['profile']['area']=='Al Barsha 3'
    assert 'ليست مرتبة بحسب المسافة' in r['answer']
    assert r['centre_search']['centres'][0]['distance_km'] is None
    assert r['next_question'].startswith('كم عمرك')


def test_resident_asks_where_and_gets_no_false_ineligible_centre():
    r=new_agent().respond('أنا مقيم في دبي بدي أجدد هويتي، وين أراجع؟')
    assert r['centre_search']['centres']==[]
    assert 'لا يعني أن الخدمة الحكومية غير متاحة' in r['answer']
    assert 'icp.gov.ae/en/customer-happiness-centers/' in r['answer']
    assert not r['centres']


def test_followup_centre_request_waits_for_category_and_emirate():
    a=new_agent()
    first=a.respond('بدي أجدد الهوية، وين أراجع؟')
    assert first['next_question'].startswith('إنت مواطن')
    second=a.respond('مواطن إماراتي',first['session_id'])
    assert second['next_question'].startswith('في أي إمارة')
    third=a.respond('دبي',first['session_id'])
    assert third['centre_search']['centres']
    assert third['next_question'].startswith('كم عمرك')


def test_urgent_whole_dialogue_with_locations():
    a=new_agent()
    r=a.respond('أنا مواطن إماراتي في دبي البرشاء عمري 29 هويتي باقي شهرين وجوازي باقي 12 شهر وعندي صورة وبدي اجدد عاجل، وين اقرب مركز؟')
    assert r['stage']=='ready'
    assert r['route']=='urgent_in_person'
    assert r['centre_search']['centres'][0]['id']=='DXB-BARSHA'
    assert all(x['distance_km'] is None for x in r['centre_search']['centres'])
    assert any(src['id']=='icp_centers' for src in r['sources'])
    assert not any(a['blocking'] for a in r['alerts'])


def test_directory_link_available_for_no_match_in_ui():
    client=TestClient(app)
    assert client.get('/assistant').status_code==200
    assert b'customer-happiness-centers/' in client.get('/assistant').content


def test_stale_alghazal_source_fixed():
    r=GovAgent(enable_audit=False).locator.recommend('Dubai','renew','citizen')
    ghazal=next(x for x in r['centres'] if x['id']=='DXB-GHAZAL')
    assert ghazal['official_url'].endswith('/customer-happiness-center-alghazal/')
