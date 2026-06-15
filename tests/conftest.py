"""Pytest fixtures — hər test üçün izolə olunmuş müvəqqəti baza."""
import pytest
import database
import app as app_module


@pytest.fixture
def client(tmp_path):
    # database.get_db() bu qlobal dəyişəni oxuyur — onu test bazasına yönəldirik
    database.DATABASE_PATH = str(tmp_path / "test.db")
    database.init_db()
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app_module.app.test_client() as c:
        yield c


def register(client, username, phone, password="parol123"):
    return client.post("/qeydiyyat", data={
        "username": username, "phone": phone,
        "password": password, "confirm": password,
    }, follow_redirects=True)


def login(client, phone, password="parol123"):
    return client.post("/giris", data={"phone": phone, "password": password},
                       follow_redirects=True)


def logout(client):
    return client.get("/cixis", follow_redirects=True)


def create_listing(client, title="Test inək"):
    return client.post("/elan-yarat", data={
        "category": "mal-qara", "subcategory": "İnək",
        "title": title, "description": "Təsvir", "price": "500",
        "region": "Bakı", "phone": "+994500000000", "quantity": "1",
    }, follow_redirects=True)
