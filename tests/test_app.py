"""MalBazari.biz əsas funksiyaların testləri."""
import database
from conftest import register, login, logout, create_listing


# ─── Əsas səhifələr ───────────────────────────────────────────

def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200


def test_about_page(client):
    assert client.get("/haqqinda").status_code == 200


def test_404(client):
    assert client.get("/movcud-olmayan-sehife").status_code == 404


def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert b"Disallow: /admin/" in r.data


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert b"<urlset" in r.data


# ─── Auth ─────────────────────────────────────────────────────

def test_register_and_profile(client):
    register(client, "Əli", "+994551111111")
    r = client.get("/profil")
    assert r.status_code == 200


def test_login_logout(client):
    register(client, "Vəli", "+994552222222")
    logout(client)
    r = login(client, "+994552222222")
    assert r.status_code == 200
    assert client.get("/profil").status_code == 200


def test_duplicate_phone_rejected(client):
    register(client, "Bir", "+994553333333")
    logout(client)
    r = register(client, "İki", "+994553333333")
    assert "artıq qeydiyyatdan" in r.get_data(as_text=True)


# ─── Elanlar ──────────────────────────────────────────────────

def test_create_listing_requires_login(client):
    r = client.get("/elan-yarat")
    assert r.status_code == 302  # girişə yönləndirir


def test_create_and_view_listing(client):
    register(client, "Satıcı", "+994554444444")
    create_listing(client, title="Gözəl camış")
    rows, total = database.get_listings()
    assert total == 1
    r = client.get(f"/elan/{rows[0]['id']}")
    assert r.status_code == 200
    assert "Gözəl camış" in r.get_data(as_text=True)


# ─── Favoritlər ───────────────────────────────────────────────

def test_favorite_toggle(client):
    register(client, "FavUser", "+994555555555")
    create_listing(client)
    lid = database.get_listings()[0][0]["id"]
    uid = database.get_user_by_phone("+994555555555")["id"]

    client.post(f"/sec/{lid}", data={}, follow_redirects=True)
    assert database.is_favorite(uid, lid) is True

    r = client.get("/secilmisler")
    assert r.status_code == 200

    client.post(f"/sec/{lid}", data={}, follow_redirects=True)
    assert database.is_favorite(uid, lid) is False


# ─── Mesajlaşma ───────────────────────────────────────────────

def test_messaging_between_users(client):
    # Satıcı elan yaradır
    register(client, "Seller", "+994556666666")
    create_listing(client)
    lid = database.get_listings()[0][0]["id"]
    seller_id = database.get_user_by_phone("+994556666666")["id"]
    logout(client)

    # Alıcı mesaj göndərir
    register(client, "Buyer", "+994557777777")
    buyer_id = database.get_user_by_phone("+994557777777")["id"]
    client.post(f"/mesaj-gonder/{lid}/{seller_id}",
                data={"body": "Salam, hələ satılır?"}, follow_redirects=True)

    # Satıcının oxunmamış mesajı olmalıdır
    assert database.count_unread(seller_id) == 1
    convo = database.get_conversation(buyer_id, seller_id, lid)
    assert len(convo) == 1
    assert convo[0]["body"] == "Salam, hələ satılır?"


def test_cannot_message_self(client):
    register(client, "Solo", "+994558888888")
    create_listing(client)
    lid = database.get_listings()[0][0]["id"]
    uid = database.get_user_by_phone("+994558888888")["id"]
    client.post(f"/mesaj-gonder/{lid}/{uid}",
                data={"body": "özümə"}, follow_redirects=True)
    assert database.count_unread(uid) == 0


# ─── Şikayət ──────────────────────────────────────────────────

def test_report_listing(client):
    register(client, "Reporter", "+994559999999")
    create_listing(client)
    lid = database.get_listings()[0][0]["id"]
    client.post(f"/sikayet/{lid}",
                data={"reason": "Saxta məlumat"}, follow_redirects=True)
    reports, total = database.get_reports()
    assert total == 1
    assert reports[0]["reason"] == "Saxta məlumat"


# ─── Filtrlər & sıralama ──────────────────────────────────────

def _post_listing(client, phone, title, price):
    return client.post("/elan-yarat", data={
        "category": "mal-qara", "subcategory": "İnək", "title": title,
        "price": price, "region": "Bakı", "phone": phone, "quantity": "1",
    }, follow_redirects=True)


def test_price_filter(client):
    register(client, "PF", "+994500000010")
    _post_listing(client, "+994500000010", "Ucuz", 100)
    _post_listing(client, "+994500000010", "Orta", 500)
    _post_listing(client, "+994500000010", "Baha", 1000)
    rows, total = database.get_listings(price_min=300, price_max=800)
    assert total == 1 and rows[0]["title"] == "Orta"


def test_sort_price_asc(client):
    register(client, "SP", "+994500000011")
    _post_listing(client, "+994500000011", "B", 900)
    _post_listing(client, "+994500000011", "A", 200)
    rows, _ = database.get_listings(sort="price_asc")
    prices = [r["price"] for r in rows]
    assert prices == sorted(prices)


def test_animal_filters(client):
    register(client, "AF", "+994500000012")
    client.post("/elan-yarat", data={
        "category": "mal-qara", "subcategory": "İnək", "title": "Südlük inək",
        "region": "Bakı", "phone": "+994500000012", "quantity": "1",
        "purpose": "Südlük", "breed": "Holşteyn", "vaccinated": "1", "weight_kg": "350",
    }, follow_redirects=True)
    assert database.get_listings(purpose="Südlük")[1] == 1
    assert database.get_listings(vaccinated=1)[1] == 1
    assert database.get_listings(weight_min=300, weight_max=400)[1] == 1
    assert database.get_listings(breed="holş")[1] == 1


# ─── OTP telefon təsdiqi ──────────────────────────────────────

def test_otp_verification_flow(client):
    register(client, "OtpUser", "+994500000013", verify=False)
    # Təsdiqlənməmiş istifadəçi elan yarada bilmir → təsdiq səhifəsinə yönəlir
    r = client.get("/elan-yarat")
    assert r.status_code == 302
    assert "/telefon-tesdiq" in r.headers["Location"]
    # Sessiyadakı OTP kodu ilə təsdiqlə
    with client.session_transaction() as s:
        code = s["otp_code"]
    client.post("/telefon-tesdiq", data={"code": code}, follow_redirects=True)
    u = database.get_user_by_phone("+994500000013")
    assert u["phone_verified"] == 1


def test_otp_wrong_code(client):
    register(client, "WrongOtp", "+994500000014", verify=False)
    client.post("/telefon-tesdiq", data={"code": "000000"}, follow_redirects=True)
    u = database.get_user_by_phone("+994500000014")
    # Yanlış kod (təsadüf üstündə deyil) → təsdiqlənməmiş qalır
    assert u["phone_verified"] == 0
