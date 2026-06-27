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


def test_clean_drops_subcategory_not_in_chosen_category():
    # "Toyuq" quş alt-kateqoriyasıdır — "mal-qara" ilə uyğun deyil, atılmalıdır
    out = ai_search._clean({"category": "mal-qara", "subcategory": "Toyuq"})
    assert out["category"] == "mal-qara"
    assert "subcategory" not in out


def test_clean_keeps_subcategory_matching_category():
    out = ai_search._clean({"category": "mal-qara", "subcategory": "İnək"})
    assert out["subcategory"] == "İnək"


def test_clean_swaps_reversed_price_and_weight():
    out = ai_search._clean({
        "price_min": 1500, "price_max": 100,
        "weight_min": 400, "weight_max": 50,
    })
    assert out["price_min"] == 100 and out["price_max"] == 1500
    assert out["weight_min"] == 50 and out["weight_max"] == 400


# ─── sort: sıralama doğrulaması ───────────────────────────────────

def test_clean_keeps_valid_sort():
    assert ai_search._clean({"sort": "price_asc"})["sort"] == "price_asc"
    assert ai_search._clean({"sort": "price_desc"})["sort"] == "price_desc"


def test_clean_drops_invalid_sort():
    assert "sort" not in ai_search._clean({"sort": "random"})
    assert "sort" not in ai_search._clean({"sort": None})


# ─── price_about: "təxminən 1200" → ±20% aralıq ───────────────────

def test_clean_price_about_builds_band():
    out = ai_search._clean({"price_about": 1200})
    assert out["price_min"] == 960   # 1200 * 0.8
    assert out["price_max"] == 1440  # 1200 * 1.2


def test_clean_price_about_ignored_when_explicit_range_given():
    # Açıq "1200-ə qədər" varsa, təxmini qiymət ona qarışmamalıdır
    out = ai_search._clean({"price_about": 1200, "price_max": 1200})
    assert out["price_max"] == 1200
    assert "price_min" not in out


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
