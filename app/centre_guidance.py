"""Offline safe centre guidance, using only the curated ICP facility records.

No geocoding, live availability, appointment booking, proximity or travel time claims.
"""
from __future__ import annotations
import re
from app.locator import CentreLocator, norm, EMIRATES

DIRECTORY = 'https://icp.gov.ae/en/customer-happiness-centers/'


def is_centre_question(message: str) -> bool:
    t = norm(message)
    # Do not confuse a why/explanation request with a facility lookup.
    if re.search(r'(?:ليش|لماذا|ليه|why)\s+', t) and not re.search(r'(?:وين|اقرب|where|nearest|which)', t):
        return False
    expressions = (
        r'وين\s+(?:اروح|اراجع|اتوجه|المركز|الفرع|اقرب|موجود)',
        r'(?:اقرب|انسب|اي|شو|اختار|اعطيني|ورجيني)\s+(?:مركز|فرع|مراكز)',
        r'(?:عنوان|عناوين|موقع|مواقع|ساعات عمل|اوقات عمل)\s+(?:مركز|مراكز|الفرع|فروع|الهيئه|icp)',
        r'(?:مراكز|مركز)\s+(?:خدمه|خدمات|مناسبه|قريبه)',
        r'where\s+(?:should|can|do)\s+i\s+(?:go|apply|visit)',
        r'(?:which|nearest|closest|nearby|find)\s+(?:icp\s+)?(?:centres?|centers?|branches?|offices?)',
        r'(?:centres?|centers?|branches?)\s+(?:near me|in dubai|in abu dhabi)',
    )
    return any(re.search(pattern,t) for pattern in expressions)


def detect_area(message: str, locator: CentreLocator | None = None) -> str | None:
    """Recognise a published centre area/alias, not a fabricated neighbourhood.

    Excludes bare emirate names and short ambiguous tokens. Uses no device location.
    """
    t = norm(message)
    known_emirates = {norm(v) for v in EMIRATES.values()} | {norm(k) for k in EMIRATES}
    candidates = []
    loc = locator or CentreLocator()
    for c in loc.centres:
        aliases = [c['area'], *c.get('area_aliases','').split('|')]
        for alias in aliases:
            a = norm(alias)
            if len(a)<4 or a in known_emirates:continue
            if re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)',t):
                candidates.append((len(a),c['area']))
    return max(candidates,key=lambda item:item[0])[1] if candidates else None


def recommendation_message(result: dict, lang: str = 'ar', count: int = 3) -> str:
    """Text restricted to the locator's structured records and an explicit disclaimer."""
    matches=result.get('centres',[])[:count]
    if lang == 'en':
        if not matches:
            return ('No documented compatible centre was found in this limited dataset. '
                    'This does NOT mean that the official service is unavailable. '
                    'Check the ICP centre directory: '+DIRECTORY)
        return ('Possible documented centres (not ranked by travel distance):\n' +
                '\n'.join(f'- {x["name"]} ({x["area"]}): {x["official_url"]}' for x in matches) +
                '\nConfirm the exact service, applicant category, working hours and urgent availability with ICP before visiting.')
    if not matches:
        return ('لا يوجد مركز متوافق موثّق ضمن عيّنة بياناتنا لهذه الحالة؛ هذا لا يعني أن الخدمة الحكومية غير متاحة. '
                'راجعي الدليل الرسمي لمراكز ICP للتحقق: '+DIRECTORY)
    return ('مراكز محتملة ضمن البيانات الموثّقة (ليست مرتبة بحسب المسافة):\n' +
            '\n'.join(f'- {x["name"]} ({x["area"]}): {x["official_url"]}' for x in matches) +
            '\nيجب تأكيد فئة المتقدم، وتوفر المعاملة وساعات العمل والخدمة العاجلة مع ICP قبل الزيارة.')


# User-facing labels remain tied to verified centre IDs and official source links.
CENTRE_LABELS_AR = {
    'DXB-BARSHA': 'مركز البرشاء لإسعاد المتعاملين',
    'DXB-RASHIDIYA': 'مركز الراشدية لإسعاد المتعاملين',
    'DXB-GHAZAL': 'مركز الغزال لإسعاد المتعاملين',
}


def final_centre_advice(result: dict, lang: str = 'ar', urgent: bool = False,
                        blocked: bool = False) -> str:
    """Re-evaluated at final decision time; never implies urgent availability.

    The first candidate is ranked by *textual area match* then service/category;
    none of the source records has verified coordinates or live opening status.
    """
    matches = result.get('centres', [])
    if not matches:
        if lang == 'en':
            return ('Centre guidance: no compatible centre was documented in this limited dataset. '
                    'This does not mean the service is unavailable. Check the ICP directory: '+DIRECTORY)
        return ('ترشيح المركز: لم نجد مركزًا مطابقًا موثّقًا في عيّنة بياناتنا لهذه الفئة والخدمة. '
                'هذا لا يعني عدم توفر الخدمة؛ تحقّق من دليل ICP: '+DIRECTORY)

    c = matches[0]
    area_match = c.get('area_text_match', False)
    if lang == 'en':
        basis = ('The area name matches your stated location and the curated record lists '
                 'this service for your applicant category.' if area_match else
                 'The curated record lists the service for your applicant category in your emirate; '
                 'there is no verified area match.')
        text = (f'Candidate centre: {c["name"]} ({c["area"]}). {basis} '
                f'Official centre page: {c["official_url"]}\n'
                'This is not a nearest-centre or verified travel-time recommendation. '
                'Confirm the service, applicant eligibility and current hours with ICP')
        if urgent:
            text += ', including whether urgent application intake is offered at this centre'
        text += ' before visiting.'
        if not urgent:
            text += ' For the standard route, start via the official digital channel when available.'
        if blocked:
            text += ' Do not visit to submit the application until blocking requirements have been resolved.'
        return text

    title = CENTRE_LABELS_AR.get(c['id'], c['name'])
    basis = ('لأن اسم منطقته يطابق المنطقة التي ذكرتها، ولأن بيانات المركز تدرج هذه الخدمة لفئتك.'
             if area_match else
             'لأن بيانات المركز تدرج هذه الخدمة لفئتك داخل الإمارة؛ لا توجد مطابقة منطقة موثّقة.')
    text = (f'المركز المرشّح ضمن بياناتنا: {title} ({c["area"]}). {basis} '
            f'رابط المركز الرسمي: {c["official_url"]}\n'
            'هذا ترشيح بحسب تطابق الخدمة والفئة والمنطقة، وليس بحسب المسافة الفعلية. '
            'يجب تأكيد الخدمة والفئة وأوقات العمل مباشرةً مع ICP')
    if urgent:
        text += '، والتأكد تحديدًا من استقبال طلبات الخدمة العاجلة في هذا المركز'
    text += ' قبل الزيارة.'
    if not urgent:
        text += ' في المسار العادي، ابدأ بالقناة الرقمية الرسمية إن كانت متاحة؛ عرض مركز بديل لا يعني وجوب زيارته.'
    if blocked:
        text += ' لا تتوجّه لتقديم الطلب قبل معالجة الملاحظات المانعة.'
    return text
