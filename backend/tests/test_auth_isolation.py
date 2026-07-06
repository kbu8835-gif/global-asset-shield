from uuid import uuid4

from fastapi.testclient import TestClient

from app import app
from database import get_user_by_email


client = TestClient(app)


def _register_user(prefix: str):
    email = f"{prefix}-{uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={"email": email, "username": prefix, "password": "12345678"},
    )
    assert response.status_code == 200
    data = response.json()
    return email, {"Authorization": f"Bearer {data['access_token']}"}, data


def test_auth_register_login_me_and_password_hash():
    email, headers, registered = _register_user("auth")
    assert registered["user"]["email"] == email
    assert registered["token_type"] == "bearer"

    login_response = client.post("/auth/login", json={"email": email, "password": "12345678"})
    assert login_response.status_code == 200
    assert login_response.json()["access_token"]

    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email

    stored = get_user_by_email(email)
    assert stored is not None
    assert stored["password_hash"] != "12345678"
    assert stored["password_hash"].startswith("pbkdf2_sha256$")


def test_user_data_isolation_for_notebook_kol_and_dna():
    email_a, headers_a, _ = _register_user("alice")
    email_b, headers_b, _ = _register_user("bob")

    notebook_response = client.post(
        "/notebook",
        headers=headers_a,
        json={"asset": "AONLY", "asset_type": "crypto", "title": "Alice only", "notes": "KOL推荐，怕踏空"},
    )
    assert notebook_response.status_code == 200
    notebook_id = notebook_response.json()["id"]

    assert any(item["id"] == notebook_id for item in client.get("/notebook", headers=headers_a).json())
    assert all(item["id"] != notebook_id for item in client.get("/notebook", headers=headers_b).json())
    assert client.get(f"/notebook/{notebook_id}", headers=headers_b).status_code == 404

    profile_response = client.post("/kol/profiles", headers=headers_a, json={"name": "Alice KOL"})
    assert profile_response.status_code == 200
    kol_id = profile_response.json()["id"]

    assert any(item["id"] == kol_id for item in client.get("/kol/profiles", headers=headers_a).json())
    assert all(item["id"] != kol_id for item in client.get("/kol/profiles", headers=headers_b).json())
    assert client.get(f"/kol/profiles/{kol_id}", headers=headers_b).status_code == 404

    dna_a = client.get("/dna", headers=headers_a).json()
    dna_b = client.get("/dna", headers=headers_b).json()
    assert dna_a["kol_dependency"] > dna_b["kol_dependency"]
    assert email_a != email_b


def test_missing_token_falls_back_to_demo_user_without_crashing():
    response = client.get("/journal")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
