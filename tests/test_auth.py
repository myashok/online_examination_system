import pytest

from accounts.models import User


@pytest.mark.django_db
def test_student_self_registers_as_student_only(api):
    response = api.post(
        "/api/auth/register/",
        {
            "name": "New Student",
            "email": "New.Student@test.edu",
            "password": "ExamPass@123",
            "role": "ADMIN",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["role"] == "STUDENT"
    assert response.data["email"] == "new.student@test.edu"
    assert "password" not in response.data
    stored = User.objects.get(email="new.student@test.edu")
    assert stored.password.startswith("argon2")
    assert stored.check_password("ExamPass@123")


@pytest.mark.django_db
def test_duplicate_email_and_weak_password_rejected(api):
    payload = {"name": "A", "email": "a@test.edu", "password": "ExamPass@123"}
    assert api.post("/api/auth/register/", payload, format="json").status_code == 201
    again = api.post("/api/auth/register/", payload, format="json")
    assert again.status_code == 400
    weak = api.post(
        "/api/auth/register/",
        {"name": "B", "email": "b@test.edu", "password": "12345678"},
        format="json",
    )
    assert weak.status_code == 400


@pytest.mark.django_db
def test_login_and_me(api):
    api.post(
        "/api/auth/register/",
        {"name": "Login User", "email": "login@test.edu", "password": "ExamPass@123"},
        format="json",
    )
    bad = api.post(
        "/api/auth/login/",
        {"email": "login@test.edu", "password": "wrong-pass"},
        format="json",
    )
    assert bad.status_code == 401
    good = api.post(
        "/api/auth/login/",
        {"email": "Login@test.edu", "password": "ExamPass@123"},
        format="json",
    )
    assert good.status_code == 200
    assert good.data["user"]["role"] == "STUDENT"
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {good.data['access']}")
    me = api.get("/api/auth/me/")
    assert me.status_code == 200
    assert me.data["email"] == "login@test.edu"


@pytest.mark.django_db
def test_inactive_user_cannot_authenticate(api, student):
    student.active = False
    student.save(update_fields=["active"])
    response = api.post(
        "/api/auth/login/",
        {"email": student.email, "password": "ExamPass@123"},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_admin_creates_faculty_and_student_cannot(api, admin_api, student_api, faculty):
    created = admin_api.post(
        "/api/users/",
        {
            "name": "New Faculty",
            "email": "new.faculty@test.edu",
            "password": "ExamPass@123",
            "role": "FACULTY",
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["role"] == "FACULTY"
    denied = student_api.post(
        "/api/users/",
        {
            "name": "Nope",
            "email": "nope@test.edu",
            "password": "ExamPass@123",
            "role": "ADMIN",
        },
        format="json",
    )
    assert denied.status_code == 403
    faculty_client = api
    from tests.conftest import login

    login(faculty_client, faculty)
    assert faculty_client.get("/api/users/").status_code == 403
    listing = admin_api.get("/api/users/")
    assert listing.status_code == 200
    assert any(row["email"] == "new.faculty@test.edu" for row in listing.data)


@pytest.mark.django_db
def test_anonymous_api_requires_token(api):
    assert api.get("/api/auth/me/").status_code == 401
    assert api.get("/api/questions/").status_code == 401
    assert api.get("/api/health/").status_code == 200
