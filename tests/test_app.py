from fastapi.testclient import TestClient

from src.app import activities, app, sessions, users


client = TestClient(app)
TEST_EMAILS = {"new.student@mergington.edu", "other.student@mergington.edu"}


def setup_function():
    users.clear()
    sessions.clear()
    client.cookies.clear()
    for activity in activities.values():
        activity["participants"] = [
            email for email in activity["participants"] if email not in TEST_EMAILS
        ]


def create_account(email="new.student@mergington.edu", password="password123"):
    return client.post("/accounts", json={"email": email, "password": password})


def login(email="new.student@mergington.edu", password="password123"):
    return client.post("/sessions", json={"email": email, "password": password})


def test_public_activities_hide_student_emails():
    response = client.get("/activities")

    assert response.status_code == 200
    chess_club = response.json()["Chess Club"]
    assert "participants" not in chess_club
    assert chess_club["participant_count"] == 2


def test_registration_requires_an_authenticated_session():
    response = client.post("/activities/Chess%20Club/signup")

    assert response.status_code == 401


def test_student_can_manage_only_their_registrations():
    assert create_account().status_code == 201
    assert login().status_code == 200

    signup = client.post("/activities/Chess%20Club/signup")
    dashboard = client.get("/me")
    cancel = client.delete("/activities/Chess%20Club/unregister")

    assert signup.status_code == 200
    assert dashboard.status_code == 200
    assert [item["name"] for item in dashboard.json()["registrations"]] == ["Chess Club"]
    assert cancel.status_code == 200
    assert "new.student@mergington.edu" not in activities["Chess Club"]["participants"]
    assert "michael@mergington.edu" in activities["Chess Club"]["participants"]


def test_passwords_are_hashed_and_password_change_revokes_session():
    assert create_account().status_code == 201
    assert users["new.student@mergington.edu"]["password_hash"] != b"password123"
    assert login().status_code == 200

    changed = client.put(
        "/accounts/password",
        json={"current_password": "password123", "new_password": "new-password123"},
    )

    assert changed.status_code == 200
    assert client.get("/me").status_code == 401
    assert login(password="password123").status_code == 401
    assert login(password="new-password123").status_code == 200


def test_recovery_code_resets_password_and_rotates_code():
    account = create_account()
    recovery_code = account.json()["recovery_code"]

    reset = client.post(
        "/accounts/password-reset",
        json={
            "email": "new.student@mergington.edu",
            "recovery_code": recovery_code,
            "new_password": "recovered-password",
        },
    )

    assert reset.status_code == 200
    assert reset.json()["recovery_code"] != recovery_code
    assert login(password="password123").status_code == 401
    assert login(password="recovered-password").status_code == 200


def test_student_cannot_cancel_another_students_registration():
    activities["Chess Club"]["participants"].append("other.student@mergington.edu")
    assert create_account().status_code == 201
    assert login().status_code == 200

    response = client.delete("/activities/Chess%20Club/unregister")

    assert response.status_code == 400
    assert "other.student@mergington.edu" in activities["Chess Club"]["participants"]


def test_logout_invalidates_the_current_session():
    assert create_account().status_code == 201
    assert login().status_code == 200
    assert client.get("/me").status_code == 200

    logout = client.delete("/sessions/current")

    assert logout.status_code == 200
    assert client.get("/session").json() == {"authenticated": False, "email": None}
    assert client.get("/me").status_code == 401
