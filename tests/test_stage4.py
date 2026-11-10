import csv
from pathlib import Path
from fastapi.testclient import TestClient
from app.locator import CentreLocator
from app.main import app


def test_dubai_citizen_renew_matches_area():
    r=CentreLocator().recommend('Dubai','renew','citizen',urgent=True,area='البرشاء')
    assert r['centres'] and r['centres'][0]['id']=='DXB-BARSHA'
    assert r['centres'][0]['area_text_match']
    assert all(x['distance_km'] is None for x in r['centres'])


def test_dubai_resident_renewal_not_misdirected():
    r=CentreLocator().recommend('Dubai','renew','resident')
    assert not r['centres']
    assert any('applicant_category_not_supported' in v['reasons'] for v in r['excluded'])


def test_resident_replacement_supported():
    r=CentreLocator().recommend('Dubai','replace','resident')
    assert len(r['centres'])>=2
    assert all('NAHDA' not in c['id'] and 'BARAHA' not in c['id'] for c in r['centres'])


def test_sharjah_closed_excluded():
    r=CentreLocator().recommend('Sharjah','renew','citizen',urgent=True)
    assert not r['centres']
    assert any('closed_or_unavailable' in c['reasons'] for c in r['excluded'])


def test_unknown_emirate_is_no_claim():
    r=CentreLocator().recommend('Ajman','renew','citizen',urgent=True)
    assert not r['centres']
    assert r['geospatial_status']=='NO_VERIFIED_COORDINATES'


def test_arabic_emirate_alias_supported():
    r=CentreLocator().recommend('دبي','new','gcc')
    assert r['centres']


def test_biometric_only_is_not_application():
    r=CentreLocator().recommend('Dubai','new','citizen')
    assert all('NAHDA' not in x['id'] for x in r['centres'])
    biometric=CentreLocator().recommend('Dubai','new','citizen',purpose='biometrics')
    assert any('NAHDA' in x['id'] for x in biometric['centres'])


def test_non_urgent_official_url_per_centre():
    r=CentreLocator().recommend('Fujairah','replace','resident')
    assert r['centres'] and all(x['official_url'].startswith('https://icp.gov.ae') for x in r['centres'])


def test_api_available_without_credentials():
    client=TestClient(app)
    r=client.get('/api/centres/recommend',params={'emirate':'Dubai','service_id':'renew','category':'citizen','area':'البرشاء','urgent':'true'})
    assert r.status_code==200 and r.json()['centres'][0]['id']=='DXB-BARSHA'
    assert client.get('/locator').status_code==200


def test_catalog_is_transparent_about_implementation():
    r=TestClient(app).get('/api/services/catalog')
    assert r.status_code==200
    rows=r.json()
    assert len(rows)>=5 and sum(x['implementation_status']=='reference_only' for x in rows)>=2


def test_all_centres_have_references_and_no_fabricated_coordinates():
    with (Path(__file__).resolve().parents[1]/'data'/'centres_verified.csv').open(encoding='utf-8-sig',newline='') as f:
        records=list(csv.DictReader(f))
    assert len(records)>=12
    assert all(not x['latitude'] and not x['longitude'] for x in records)
    assert all(x['source_url'].startswith('https://icp.gov.ae') for x in records)
