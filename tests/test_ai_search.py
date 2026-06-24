"""AI axtarış (ai_search) testləri — şəbəkə/AI olmadan, təmizləmə məntiqini yoxlayır."""
import ai_search


# ─── _clean: filtr təmizləmə/doğrulama ───────────────────────────

def test_clean_keeps_valid_values():
    raw = {
        "category": "mal-qara", "subcategory": "İnək", "region": "Gəncə",
        "price_max": 1500, "purpose": "Südlük", "vaccinated": True,
        "breed": "Holştayn", "keywords": "südlük inək",
    }
    out = ai_search._clean(raw)
    assert out["category"] == "mal-qara"
    assert out["subcategory"] == "İnək"
    assert out["region"] == "Gəncə"
    assert out["price_max"] == 1500
    assert out["purpose"] == "Südlük"
    assert out["vaccinated"] == 1
    assert out["breed"] == "Holştayn"
    assert out["keywords"] == "südlük inək"


def test_clean_drops_invalid_category_and_region():
    raw = {"category": "uyghun-deyil", "region": "Paris", "purpose": "XYZ"}
    out = ai_search._clean(raw)
    assert "category" not in out
    assert "region" not in out
    assert "purpose" not in out


def test_clean_handles_numeric_strings_and_negatives():
    raw = {"price_min": "100", "price_max": "abc", "weight_max": -5}
    out = ai_search._clean(raw)
    assert out["price_min"] == 100
    assert "price_max" not in out   # parse oluna bilmir
    assert "weight_max" not in out  # mənfi rədd edilir


def test_clean_vaccinated_false():
    assert ai_search._clean({"vaccinated": False})["vaccinated"] == 0
    assert "vaccinated" not in ai_search._clean({"vaccinated": None})


# ─── parse_query: açar/giriş yoxlaması (şəbəkəyə çıxmadan) ────────

def test_parse_query_no_api_key_returns_none():
    assert ai_search.parse_query("südlük inək", "") is None


def test_parse_query_empty_text_returns_none():
    assert ai_search.parse_query("", "fake-key") is None


# ─── Route: API açarı olmadıqda adi axtarışa keçir (fallback) ─────

def test_ai_route_fallback_without_api_key(client):
    # Açar yoxdur → adi axtarış nəticə səhifəsi (200), sayt sınmır
    r = client.get("/ai-axtar?q=inek")
    assert r.status_code == 200


def test_ai_route_empty_query_redirects_home(client):
    r = client.get("/ai-axtar?q=")
    assert r.status_code == 302
