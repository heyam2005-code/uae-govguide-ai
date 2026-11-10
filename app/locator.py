"""Service-compatibility-first ICP centre selection. Offline; does NOT calculate distances."""
from __future__ import annotations
from pathlib import Path
import csv,re,unicodedata
ROOT=Path(__file__).resolve().parents[1]
EMIRATES={'دبي':'Dubai','dubai':'Dubai','ابوظبي':'Abu Dhabi','أبوظبي':'Abu Dhabi','abu dhabi':'Abu Dhabi','sharjah':'Sharjah','الشارقة':'Sharjah','الشارقه':'Sharjah','راس الخيمة':'Ras Al Khaimah','ras al khaimah':'Ras Al Khaimah','الفجيرة':'Fujairah','fujairah':'Fujairah','ام القيوين':'Umm Al Quwain','umm al quwain':'Umm Al Quwain','العين':'Abu Dhabi','ajman':'Ajman','عجمان':'Ajman'}
def norm(x):
 x=(x or '').casefold().replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه').replace('ى','ي')
 return re.sub(r'\s+',' ',x).strip()
def load():
 with (ROOT/'data'/'centres_verified.csv').open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
class CentreLocator:
 def __init__(self):self.centres=load()
 def recommend(self,emirate,service_id,category,urgent=False,area=None,limit=6,purpose='application'):
  em=EMIRATES.get(norm(emirate),emirate or '')
  included=[]; excluded=[]
  for c in self.centres:
   if norm(c['emirate'])!=norm(em):continue
   reasons=[]
   if c['status']!='active':reasons.append('closed_or_unavailable')
   if purpose=='biometrics':
    if 'biometrics' not in c['services'].split('|'):reasons.append('biometrics_not_listed')
   else:
    if service_id not in ('renew','new','replace'):reasons.append('service_not_supported')
    elif service_id not in c['services'].split('|'):reasons.append('service_not_listed')
    elif category not in c[service_id+'_categories'].split('|'):reasons.append('applicant_category_not_supported')
    if urgent and c['urgent_intake']=='no':reasons.append('urgent_not_listed')
   if reasons:
    excluded.append({'id':c['id'],'name':c['name'],'reasons':reasons,'source_url':c['source_url']});continue
   possible=[c['area'],c['name']]+c['area_aliases'].split('|')
   user_area=norm(area)
   area_match=bool(user_area and any(user_area==norm(part) or (len(user_area)>=4 and user_area in norm(part)) for part in possible if part))
   included.append({'id':c['id'],'name':c['name'],'emirate':c['emirate'],'area':c['area'],'address':c['address'],
                    'hours':c['hours'],'status':c['status'],'official_url':c['source_url'],
                    'urgent_confirmation_required':bool(urgent),'area_text_match':area_match,
                    'ranking_basis':('مطابقة اسم المنطقة + توفر الخدمة والفئة' if area_match else 'توفر الخدمة والفئة داخل الإمارة'),
                    'distance_km':None,'coordinates_verified':False,
                    'notice':'تأكد من المركز مباشرة من ساعات العمل وخدمة المعاملة العاجلة قبل الزيارة.' if urgent else 'تأكد من أوقات العمل وتوافر المعاملة قبل الزيارة.'})
  included.sort(key=lambda c:(not c['area_text_match'],c['name']))
  return {'centres':included[:limit],'excluded':excluded,'total_eligible':len(included),'emirate':em,
          'method':'verified_service_category_then_area_text_match','geospatial_status':'NO_VERIFIED_COORDINATES',
          'message':'ترشيح مبدئي حسب توفر الخدمة وفئة المتقدم، وليس حسب أقصر مسافة. لا توجد إحداثيات موثقة لحساب المسافات.'}
