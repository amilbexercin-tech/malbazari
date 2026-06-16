# 🐄 MalBazari.biz — Tam Layihə Vəziyyəti

> Son yenilənmə: 2026-06-16. Bu sənəd saytda nə olduğunu, nəyin qurulduğunu və nəyin qaldığını izah edir.

---

## 1. Sayt nədir?
Azərbaycan üçün **heyvan alqı-satqı elan platforması** — Mal-Qara, Quşçuluq, Arıçılıq.
3 dildə (AZ/RU/EN), 58 rayon, heyvana xas sahələrlə.

- **Canlı link:** https://web-production-516be.up.railway.app
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
- ✅ Parametrlər (sayt adı, əlaqə, Anthropic API açarı)
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
| **Öz domeni (malbazari.az)** | ⏳ Qalıb |

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
1. **Real SMS** qoş (Twilio və ya yerli AZ provayder) → telefon təsdiqi + parol bərpası tam işləsin
   - Sonra `.env`-də: `REQUIRE_PHONE_VERIFICATION=1`, `SMS_PROVIDER=twilio`, açarlar
2. **Monitorinq** — kod hazırdır, yalnız xidmətə qoşmaq qalır:
   - **UptimeRobot** (pulsuz) — `https://<sayt>/health` linkini əlavə et → sayt düşəndə email/bildiriş
   - **Sentry** (pulsuz) — sentry.io-da layihə yarat, Railway Variables-ə `SENTRY_DSN` əlavə et → kod xətası olanda səbəbi ilə xəbər
3. **Öz domenin** (malbazari.az) — alıb Railway-ə bağlamaq
4. **Kənar yedək (Telegram)** — kod hazırdır: Railway Variables-ə `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` əlavə et → gündəlik yedək avtomatik Telegram-a gəlsin. (Əl ilə: admin "Yedək Al" ilə zip-i kompüterə də endirmək olar.)
5. (Böyümə) Məxfilik/Şərtlər səhifələri, satıcı reytinqi, saxlanan axtarış, PWA

### ✅ Yeni həll olunanlar (2026-06-16)
- **Data itməsi düzəldildi** — Railway Volume `/data`-a mount + `DATA_DIR=/data`. Səbəb: əvvəl data müvəqqəti `/app` diskində idi, hər deploy/restart-da silinirdi (admin 2FA sıfırlanırdı, elanlar yox olurdu).
- **Sağlamlıq səhifəsi** (`/admin/saglamliq`) + startup diaqnostikası əlavə olundu.
- **Server regionu** Avropaya keçirildi.
- **`/health`** public endpoint (UptimeRobot üçün) əlavə olundu.

---

## 12. Vacib qeydlər
- **Admin parolu** Railway Variables-dadır (`ADMIN_PASSWORD`) — kodda deyil
- **2FA bərpa kodlarını** saxla (telefon itsə yeganə giriş yolu) — Hesab ayarları → "Bərpa kodları yarat"
- **Testlər:** 25 avtomatik test (hamısı keçir)
- Telefon təsdiqi **hələlik söndürülüb** (real SMS qoşulanda açılacaq)
```
```
