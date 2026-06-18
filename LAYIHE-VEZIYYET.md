# 🐄 MalQara — Tam Layihə Vəziyyəti

> Son yenilənmə: 2026-06-18. Bu sənəd saytda nə olduğunu, nəyin qurulduğunu və nəyin qaldığını izah edir.
>
> **⚠️ Rebrand (2026-06-18):** Layihə **MalBazari → HeyvanBazar → MalQara** adına keçdi (yekun: **MalQara**). Səbəblər: (1) `malbazari.az`/`.com` eyni adlı canlı rəqibdədir; (2) `heyvanbazari.az` (bir hərf fərqlə) artıq mövcuddur — qarışıqlıq riski. Yekun brend **MalQara** seçildi — `malqara.az` + `malqara.com` **boşdur** (təsdiqləndi), ikisi də alınacaq. Loqo: inək+qoyun+toyuq+sünbül emblemi (3D, animasiyalı).

---

## 1. Sayt nədir?
Azərbaycan üçün **heyvan alqı-satqı elan platforması** — Mal-Qara, Quşçuluq, Arıçılıq.
3 dildə (AZ/RU/EN), 58 rayon, heyvana xas sahələrlə.

- **Canlı link:** https://web-production-516be.up.railway.app (öz domeni: **malqara.az** — alınma mərhələsində)
- **Kod (GitHub):** https://github.com/amilbexercin-tech/malbazari
- **Admin login:** `@Superlahiye@` + parol (Railway Variables-dakı `ADMIN_PASSWORD`) + 2FA (Authenticator)

---

## 2. Texnologiyalar (stack)
- **Backend:** Python + Flask
- **Baza:** SQLite (tək fayl)
- **Server (production):** Gunicorn
- **Şəkil emalı:** Pillow
- **2FA:** pyotp + qrcode
- **Rate-limit:** Flask-Limiter
- **CSRF:** Flask-WTF
- **Hosting:** Railway (Google Cloud üzərində)
- **Versiya nəzarəti:** Git + GitHub

---

## 3. İstifadəçi funksiyaları (A–Z)
- ✅ Qeydiyyat / giriş / çıxış (telefon + şifrə)
- ✅ Elan yaratmaq / redaktə / silmək (5 şəkilə qədər, avtomatik optimallaşdırma)
- ✅ Heyvana xas sahələr: məqsəd (südlük/ətlik/damazlıq/yumurtalıq), cins, yaş, peyvənd, çəki (kq)
- ✅ Axtarış + filtrlər: kateqoriya, alt-kateqoriya, rayon, **qiymət aralığı, çəki aralığı, məqsəd, peyvənd, cins**
- ✅ Sıralama: ən yeni, ən köhnə, qiymət ↑, qiymət ↓
- ✅ Elan detalları + baxış sayğacı
- ✅ **Xəritədə yer** (Leaflet/OpenStreetMap — elan yaradanda pin qoyulur, detalda göstərilir)
- ✅ **Mesajlaşma** (istifadəçilər arası, inbox + söhbət, oxunmamış sayğacı)
- ✅ **Favoritlər** (ürək düyməsi, "Seçilmişlər" səhifəsi)
- ✅ **Şikayət** sistemi (elanları report etmək)
- ✅ Zəng + WhatsApp düymələri
- ✅ **3 dil** (AZ/RU/EN) — dəyişdirici navbar-da
- ✅ Hesab ayarları (ad + şifrə dəyişmə)
- ✅ Parol bərpası (telefon kodu ilə) — *real SMS qoşulanda tam işləyəcək*
- ✅ Elanlar 30 gün sonra avtomatik silinir

---

## 4. Admin panel funksiyaları
- ✅ Dashboard (statistika)
- ✅ Elanların idarəsi (bax / sil)
- ✅ İstifadəçilərin idarəsi (bax / sil)
- ✅ Şikayətlərin idarəsi (həll et / elanı sil)
- ✅ Parametrlər (sayt adı, əlaqə, Anthropic API açarı, **sosial şəbəkə linkləri**)
- ✅ **Yedək Al** (baza + şəkilləri zip kimi yüklə)
- ✅ Kod redaktoru (yalnız şablon/mətn — `.py` təhlükəsizlik üçün bağlı)
- ✅ **Sağlamlıq səhifəsi** (`/admin/saglamliq`) — data kalıcı diskdə saxlanırmı, problemlər siyahısı, canlı yazma testi
- ✅ Bütün admin **2FA arxasında**

---

## 5. Təhlükəsizlik (nə qurulub)
- ✅ Şifrələr hash-lənir (werkzeug)
- ✅ **CSRF qoruması** bütün formalarda
- ✅ **SQL inyeksiya** qoruması (parametrli sorğular)
- ✅ **XSS** qoruması (Jinja avto-escape)
- ✅ **Admin 2FA** (TOTP / Google Authenticator) + 8 bərpa kodu
- ✅ **Rate-limiting** (giriş, qeydiyyat, mesaj, şikayət, OTP brute-force qarşısı)
- ✅ SECRET_KEY kodda deyil (env / fayl)
- ✅ Debug rejimi production-da SÖNDÜRÜLÜB
- ✅ Sessiya kukiləri: HTTPOnly, SameSite, Secure (HTTPS)
- ✅ Şəkil təhlükəsizliyi (məzmun yoxlanır, yenidən kodlanır)
- ✅ Kod redaktorunda `.py`/`.db` redaktəsi BAĞLI (RCE qarşısı)
- ✅ HTTPS (Railway avtomatik)

---

## 6. Verilənlər bazası
- **Növ:** SQLite — ayrıca server YOX, tək fayl
- **Production-da yer:** Railway **kalıcı diskində** `/data/malbazari.db`
- **Lokalda yer:** `C:\Users\amilb\malbazari\malbazari.db`
- **Cədvəllər:** users, listings, messages, favorites, reports, settings, edit_history
- **Şəkillər:** bazada deyil — `/data/static/uploads/` (production), bazada yalnız adları
- **Yedək:** gündəlik avtomatik (`/data/backups`) + admin "Yedək Al" düyməsi

---

## 7. Deploy / Qoşulmalar (nələri qurmuşuq)
| Komponent | Vəziyyət |
|---|---|
| **GitHub repo** | ✅ Bağlı (kod orada) |
| **Railway deploy** | ✅ Canlı |
| **Kalıcı disk (Volume)** | ✅ `/data` mount + `DATA_DIR=/data` (data itmir — 2026-06-16 təsdiqləndi) |
| **Env Variables** | ✅ SECRET_KEY, DATA_DIR, SESSION_COOKIE_SECURE, ADMIN_PHONE, ADMIN_PASSWORD |
| **HTTPS** | ✅ Avtomatik |
| **Avtomatik deploy** | ✅ push → Railway yenilənir |
| **Avtomatik backup** | ✅ Gündəlik (kalıcı diskə) + opsional Telegram kənar yedək |
| **Server regionu** | ✅ Avropa (2026-06-16) |
| **Uptime health linki** | ✅ `/health` (UptimeRobot üçün hazır) |
| **Öz domeni (malqara.az + .com)** | ⏳ Alınır — kod hazır (`CANONICAL_HOST` env + 301 yönləndirmə) |

---

## 8. İş axını (necə dəyişiklik edirik)
```
Sən deyirsən  →  Mən lokALda düzəldib test edirəm  →  git push  →  Railway avtomatik deploy edir  →  Sayt yenilənir
```
Sən terminala toxunmursan. Sayt sınsa, Railway-dən bir kliklə geri qaytarmaq olur.

---

## 9. Pul / Xərc (Railway)
- **Plan:** Hobby ~$5/ay (istifadəyə görə; bizim app adətən bu məbləğdə qalır)
- **Ödəniş:** Railway → Settings → Billing → kart (aylıq avtomatik)
- **Məsləhət:** "Usage Limit" qoy ki, büdcəni keçməsin

---

## 10. Tutum (nə qədər dözər)
- Ümumi: 100,000+ elan / istifadəçi — problem deyil
- Eyni anda aktiv: ~50–200 nəfər rahat, gündə ~5,000–20,000 ziyarətçi
- İlk məhdudiyyət: **disk (şəkillər ~5 GB ≈ 25–40 min şəkil)**
- Böyüyəndə: PostgreSQL + bulud storage + Redis (hamısı sonra qoşula bilər)

---

## 11. QALAN İŞLƏR (sabah / sonra üçün)
1. **Real SMS** — KOD HAZIRDIR (LSIM.az inteqrasiyası yazılıb), ⏳ yalnız LSIM açarı gözlənilir
   - LSIM-dən: login + parol + təsdiqlənmiş "MalQara" göndərən ad
   - Açar gələndə Railway Variables: `SMS_PROVIDER=lsim`, `SMS_LOGIN`, `SMS_PASSWORD`, `SMS_SENDER=MalQara`, `REQUIRE_PHONE_VERIFICATION=1`
   - LSIM portal: sendsms.az · API sənəd: docs.lsim.az
   - (Alternativ provayderlər: Twilio kodu da hazır; MOBIS.az üçün API uyğunlaşdırıla bilər)
2. **Öz domenin** (malqara.az + malqara.com) — almaq → Railway-ə bağlamaq → Railway Variables-ə `CANONICAL_HOST=malqara.az` qoymaq (kod artıq hazır: digər bütün hostlar avtomatik .az-a 301 yönlənir, `/health` istisna)
3. **Sosial səhifə linkləri** — TikTok/Instagram/WhatsApp səhifələri açılanda Admin → Parametrlər → "Sosial Şəbəkələr"-ə linkləri yapışdır
4. (Böyümə) Məxfilik/Şərtlər səhifələri, satıcı reytinqi, saxlanan axtarış, PWA

### ✅ Bu gün edilənlər (2026-06-18)
- **🔴 Rebrand: MalBazari → HeyvanBazar.** Səbəb: `malbazari.az`/`.com` artıq eyni adlı canlı rəqibdədir. Yeni brend `heyvanbazar` (.az + .com boş, ikisi də alınacaq).
  - Kodda dəyişdi: navbar/footer/about brendi, meta, SMS mətni, 2FA issuer, diaqnostika başlığı, default sayt adı/email, env/şərhlər.
  - **Avtomatik miqrasiya:** canlı bazadakı saxlanmış `site_name`/`contact_email` köhnə standart dəyərdirsə avtomatik yenilənir (adminin əl ilə qoyduğu dəyər pozulmur).
  - **Toxunulmadı (texniki):** `malbazari.db` fayl adı/yolu, backup fayl adları — datanı sındırmamaq üçün.
- **Canonical domen yönləndirməsi əlavə olundu** (`app.py`, `CANONICAL_HOST` env). Təyin olunsa, bütün digər hostlar (köhnə railway linki, .com, www) → `https://heyvanbazar.az`-a 301. `/health` istisna (monitorinq pozulmur). Env qoyulmayana qədər təsiri yoxdur.
- **Domen araşdırması:** `malbazari.az`/`.com` rəqibdə (api.malbazari.az, ~273 elan, premium 3/7/12₼, Instagram @malbazari.az, WhatsApp +994 70 566 55 11). `heyvanbazar.az` + `heyvanbazar.com` boş — yeni brend kimi seçildi.

### ✅ Edilənlər (2026-06-16)
- **🔴 Data itməsi düzəldildi** (ən vacib) — Railway Volume `/data`-a mount + `DATA_DIR=/data`. Səbəb: əvvəl data müvəqqəti `/app` diskində idi, hər deploy/restart-da silinirdi (admin hər girişdə yenidən QR/2FA istəyirdi, elanlar ~1 saatdan sonra yox olurdu).
- **Sağlamlıq səhifəsi** (`/admin/saglamliq`) + startup diaqnostikası — data kalıcı diskdə saxlanırmı, problemlər siyahısı, canlı yazma testi, Telegram test düyməsi.
- **Server regionu** Avropaya keçirildi.
- **Monitorinq qoşuldu:** `/health` public endpoint + **UptimeRobot** (sayt düşəndə xəbər) + **Sentry** (`SENTRY_DSN`, kod xətası xəbəri).
- **Kənar yedək — Telegram qoşuldu:** gündəlik yedək avtomatik Telegram-a gəlir. **Gündə 1 dəfə, gün sonunda** (AZ vaxtı, saat 23:00; `BACKUP_HOUR`). Bazadakı tarixlə idarə olunur — restart/worker təkrar göndərmir.
- **Footer sosial ikonlar:** Facebook silindi → **TikTok** əlavə olundu (sıra: TikTok, Instagram, WhatsApp). Linklər Admin → Parametrlər → "Sosial Şəbəkələr"-dən idarə olunur.
- **SMS (LSIM) kodu yazıldı** — açar gözlənilir (bax: Qalan işlər #1).

---

## 12. Vacib qeydlər
- **Admin parolu** Railway Variables-dadır (`ADMIN_PASSWORD`) — kodda deyil
- **2FA bərpa kodlarını** saxla (telefon itsə yeganə giriş yolu) — Hesab ayarları → "Bərpa kodları yarat"
- **Testlər:** 25 avtomatik test (hamısı keçir)
- Telefon təsdiqi **hələlik söndürülüb** (real SMS qoşulanda açılacaq)
```
```
