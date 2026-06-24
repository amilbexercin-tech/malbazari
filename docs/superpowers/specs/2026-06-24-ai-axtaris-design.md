# AI Axtarış (Natural-Language Search) — Dizayn

> Tarix: 2026-06-24 · Layihə: MalQara.az

## Məqsəd
Adi filtr sahələri əvəzinə istifadəçi **adi dildə** nə axtardığını yazsın (məs.
"Gəncədə 1500 manata qədər südlük inək"), sistem də uyğun elanları tapıb göstərsin.
Filtrlər silinmir — "Ətraflı filtr" düyməsi altında gizlənir (fallback + güclü
istifadəçi üçün).

## Yanaşma (seçilmiş)
**AI → filtr tərcüməçi.** AI sorğunu mövcud axtarış parametrlərinə çevirir, sonra
hazır `db.get_listings()` işləyir.

- **Niyə:** ucuz (sorğu başına ~$0.0001), sürətli, elan sayından asılı deyil,
  mövcud kodu təkrar istifadə edir.
- **Rədd edilən alternativlər:** (B) bütün elanları AI-a göndərmək — bahalı/yavaş,
  token limiti; (C) embedding semantik axtarış — əlavə infrastruktur, hələ erkəndir.

## Komponentlər

### 1. `ai_search.py` (yeni modul)
- `parse_query(text, api_key) -> dict | None`
- Anthropic Haiku (`claude-haiku-4-5-20251001`) çağırır.
- System prompt CATEGORIES (slug+ad+alt-kateqoriya), REGIONS, PURPOSES siyahısını
  verir və ciddi JSON qaytarmasını tələb edir.
- Qaytarılan açarlar (hamısı opsional): `category`, `subcategory`, `region`,
  `price_min`, `price_max`, `weight_min`, `weight_max`, `purpose`, `vaccinated`,
  `breed`, `keywords`.
- Çıxışı **təmizləyir/doğrulayır**: yalnız mövcud slug/region/purpose qəbul edilir
  (model uydurarsa atılır). JSON parse alınmasa `None`.
- Şəbəkə/parse xətası → `None` (heç vaxt exception atmır).

### 2. Route: `GET /ai-axtar` (app.py)
- `q` parametrini alır.
- `db.get_setting('anthropic_api_key')` yoxdursa → adi `search`-ə yönləndir.
- `ai_search.parse_query` çağırır. `None` qayıdarsa → `keywords=q` ilə adi axtarış
  (fallback). Uğurlu olarsa filtrləri `db.get_listings()`-ə ötürür.
- `templates/ai_search.html` render edir: AI-ın anladığı filtrləri "çip" kimi göstərir
  + nəticə şəbəkəsi (mövcud `partials/listing_card.html` + paginasiya).
- `@limiter.limit("20 per hour")` — xərc/spam qoruması. `@csrf.exempt` lazım deyil (GET).

### 3. Frontend
- `index.html` hero: əsas qutu **AI axtarış** olur (böyük input + "✨ AI ilə axtar").
  Altında `⚙ Ətraflı filtr ▾` düyməsi — klikləyəndə köhnə kateqoriya+söz forması açılır
  (JS toggle, CSS ilə).
- `ai_search.html`: nəticə səhifəsi, yuxarıda "AI nə anladı: Gəncə · südlük · ≤1500₼"
  çipləri, "Filtri dəyişdir" linki adi axtarışa.
- i18n: AZ/RU/EN açarları (`ai_search_title`, `ai_search_ph`, `ai_search_btn`,
  `ai_understood`, `advanced_filter`).

## Data axını
```
İstifadəçi mətn → /ai-axtar?q=... → ai_search.parse_query (Haiku)
   → təmizlənmiş filtr dict → db.get_listings(**filters) → ai_search.html
   (xəta/açar yox → adi keyword axtarış)
```

## Xəta idarəsi
- API açarı yox → adi axtarış (istifadəçi fərq görmür).
- AI xətası / yanlış JSON → adi keyword axtarış.
- Model uydurma slug/region → atılır (yalnız real dəyərlər).
- Rate limit aşılarsa → 429 səhifəsi (mövcud handler).

## Test
- `ai_search.parse_query` üçün: mock Anthropic cavabı ilə JSON parse + təmizləmə
  (yanlış slug atılır, yaxşı dəyər qalır), pis JSON → None.
- Route üçün: API açarı olmadıqda fallback işləyir; `q` boşdursa index-ə yönləndirir.
- Mövcud 25 test pozulmamalıdır.

## Əhatə xaricində (sonraya)
- Embedding/semantik axtarış.
- AI nəticələrinin "ağıllı sıralanması" (relevance scoring).
- Səs ilə axtarış.
