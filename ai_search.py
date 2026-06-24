# -*- coding: utf-8 -*-
"""AI axtarış: istifadəçinin adi dildə yazdığı sorğunu mövcud axtarış filtrlərinə
çevirir. Anthropic Haiku (ucuz/sürətli) çağırır. Heç vaxt exception atmır —
xəta/açar yoxdursa None qaytarır, çağıran tərəf adi axtarışa keçir."""

import json
from config import CATEGORIES, REGIONS, PURPOSES

# Ucuz və sürətli model — sorğu→filtr tərcüməsi üçün kifayətdir.
MODEL = "claude-haiku-4-5-20251001"

_VALID_CATEGORIES = set(CATEGORIES.keys())
_VALID_REGIONS = set(REGIONS)
_VALID_PURPOSES = set(PURPOSES)
# Bütün alt-kateqoriyalar (kateqoriyadan asılı olmadan doğrulama üçün)
_VALID_SUBCATEGORIES = {s for c in CATEGORIES.values() for s in c['subcategories']}


def _build_system_prompt():
    cats = []
    for slug, c in CATEGORIES.items():
        subs = ', '.join(c['subcategories'])
        cats.append(f'  - "{slug}" ({c["name"]}): alt-kateqoriyalar = [{subs}]')
    cats_txt = '\n'.join(cats)
    regions_txt = ', '.join(REGIONS)
    purposes_txt = ', '.join(PURPOSES)
    return f"""Sən Azərbaycan heyvan elan saytı (MalQara.az) üçün axtarış köməkçisisən.
İstifadəçinin adi dildə yazdığı sorğunu axtarış filtrlərinə çevir.

KATEQORİYALAR (slug istifadə et):
{cats_txt}

RAYONLAR: {regions_txt}

MƏQSƏDLƏR: {purposes_txt}

Yalnız aşağıdakı sahələri olan TƏMİZ JSON qaytar (izahat yox, markdown yox):
{{
  "category": "<slug və ya null>",
  "subcategory": "<dəqiq alt-kateqoriya adı və ya null>",
  "region": "<dəqiq rayon adı və ya null>",
  "price_min": <ədəd və ya null>,
  "price_max": <ədəd və ya null>,
  "weight_min": <kq ədəd və ya null>,
  "weight_max": <kq ədəd və ya null>,
  "purpose": "<dəqiq məqsəd və ya null>",
  "vaccinated": <true, false və ya null>,
  "breed": "<cins adı və ya null>",
  "keywords": "<qalan açar sözlər və ya null>"
}}

Qaydalar:
- Yalnız verilmiş siyahılardan dəqiq dəyər seç; uyğun gəlməsə null qoy.
- "ucuz" qiymət filtri deyil — keywords-ə də qoyma, sadəcə nəzərə alma.
- Əmin olmadığın sahəni null burax. Heç bir sahə uydurma."""


def _coerce_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip().replace(',', '.')
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _clean(raw):
    """Modelin qaytardığı dict-i təmizlə: yalnız real/etibarlı dəyərləri saxla."""
    out = {}
    cat = raw.get('category')
    if cat in _VALID_CATEGORIES:
        out['category'] = cat
    sub = raw.get('subcategory')
    if sub in _VALID_SUBCATEGORIES:
        out['subcategory'] = sub
    region = raw.get('region')
    if region in _VALID_REGIONS:
        out['region'] = region
    purpose = raw.get('purpose')
    if purpose in _VALID_PURPOSES:
        out['purpose'] = purpose
    for k in ('price_min', 'price_max', 'weight_min', 'weight_max'):
        n = _coerce_num(raw.get(k))
        if n is not None and n >= 0:
            out[k] = n
    vacc = raw.get('vaccinated')
    if vacc is True:
        out['vaccinated'] = 1
    elif vacc is False:
        out['vaccinated'] = 0
    breed = raw.get('breed')
    if isinstance(breed, str) and breed.strip():
        out['breed'] = breed.strip()[:100]
    kw = raw.get('keywords')
    if isinstance(kw, str) and kw.strip():
        out['keywords'] = kw.strip()[:200]
    return out


def diagnose(text, api_key):
    """MÜVƏQQƏTİ diaqnostika — AI çağırışının harada sındığını göstərir.
    Admin /admin/ai-test endpoint-i istifadə edir. Sonra silinə bilər."""
    info = {'has_key': bool(api_key), 'model': MODEL, 'step': 'start',
            'error': None, 'raw': None, 'parsed': None}
    if not (text and api_key):
        info['step'] = 'missing-input'
        return info
    try:
        import anthropic
        info['anthropic_version'] = getattr(anthropic, '__version__', '?')
        client = anthropic.Anthropic(api_key=api_key)
        info['step'] = 'calling-api'
        msg = client.messages.create(
            model=MODEL, max_tokens=400,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": text[:500]}],
        )
        info['step'] = 'got-response'
        content = msg.content[0].text.strip()
        info['raw'] = content[:1000]
        info['parsed'] = parse_query(text, api_key)
        info['step'] = 'done'
    except Exception as e:
        info['step'] = 'exception'
        info['error'] = f'{type(e).__name__}: {e}'
    return info


def parse_query(text, api_key):
    """Sorğu mətnini təmizlənmiş filtr dict-inə çevirir. Xətada None."""
    text = (text or '').strip()
    if not text or not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": text[:500]}],
        )
        content = msg.content[0].text.strip()
        # Ehtiyat: markdown ``` blokunu təmizlə
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
        # İlk { ilə son } arasını götür (model artıq mətn yazsa belə)
        start, end = content.find('{'), content.rfind('}')
        if start == -1 or end == -1:
            return None
        raw = json.loads(content[start:end + 1])
        if not isinstance(raw, dict):
            return None
        return _clean(raw)
    except Exception:
        return None
