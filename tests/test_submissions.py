"""
Tests for submission and editorial workflow endpoints.
"""
import pytest
from httpx import AsyncClient


async def _signup_and_get_token(client: AsyncClient, email: str, password: str = "testpass123", name: str = "Test User") -> str:
    resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": password,
        "display_name": name,
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _make_contributor(client: AsyncClient, email: str) -> str:
    """Sign up and upgrade user to contributor role via direct DB manipulation."""
    from app.models.user import User, UserRole
    from tests.conftest import TestSessionLocal
    from sqlalchemy import select

    token = await _signup_and_get_token(client, email)

    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.role = UserRole.contributor
        await session.commit()

    # Re-login to get fresh token with updated role
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123",
    })
    return resp.json()["access_token"]


async def _make_editor(client: AsyncClient, email: str) -> str:
    """Sign up and upgrade user to editor role."""
    from app.models.user import User, UserRole
    from tests.conftest import TestSessionLocal
    from sqlalchemy import select

    await _signup_and_get_token(client, email)

    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.role = UserRole.editor
        await session.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123",
    })
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_submission_as_contributor(client: AsyncClient) -> None:
    """Contributors can create submissions."""
    token = await _make_contributor(client, "sub_create@test.com")

    resp = await client.post(
        "/api/v1/submissions",
        json={
            "title": "My Essay",
            "category": "essay",
            "body_text": "This is the body of my essay.",
            "content_warnings": ["mentions of illness"],
            "anonymous_byline": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Essay"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_reader_cannot_create_submission(client: AsyncClient) -> None:
    """Readers (non-contributors) cannot create submissions."""
    token = await _signup_and_get_token(client, "reader_sub@test.com")

    resp = await client.post(
        "/api/v1/submissions",
        json={
            "title": "Unauthorized Essay",
            "category": "essay",
            "body_text": "Body.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_draft(client: AsyncClient) -> None:
    """Contributors can submit a draft, changing its status to 'submitted'."""
    token = await _make_contributor(client, "sub_submit@test.com")

    create_resp = await client.post(
        "/api/v1/submissions",
        json={
            "title": "Draft to Submit",
            "category": "poetry",
            "body_text": "Petals fall.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    submission_id = create_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_list_my_submissions(client: AsyncClient) -> None:
    """Contributors can list only their own submissions."""
    token = await _make_contributor(client, "sub_list@test.com")

    await client.post(
        "/api/v1/submissions",
        json={"title": "My Sub 1", "category": "essay", "body_text": "Body 1."},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/v1/submissions",
        json={"title": "My Sub 2", "category": "poetry", "body_text": "Body 2."},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/submissions/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_delete_draft_submission(client: AsyncClient) -> None:
    """Contributors can delete their own draft submissions."""
    token = await _make_contributor(client, "sub_delete@test.com")

    create_resp = await client.post(
        "/api/v1/submissions",
        json={"title": "To Delete", "category": "essay", "body_text": "Bye."},
        headers={"Authorization": f"Bearer {token}"},
    )
    submission_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_cannot_delete_submitted(client: AsyncClient) -> None:
    """Cannot delete a submission that's already been submitted."""
    token = await _make_contributor(client, "sub_no_del@test.com")

    create_resp = await client.post(
        "/api/v1/submissions",
        json={"title": "Submitted", "category": "essay", "body_text": "Body."},
        headers={"Authorization": f"Bearer {token}"},
    )
    submission_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )

    del_resp = await client.delete(
        f"/api/v1/submissions/{submission_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 400


@pytest.mark.asyncio
async def test_editorial_status_change(client: AsyncClient) -> None:
    """Editors can change submission status following valid transitions."""
    contrib_token = await _make_contributor(client, "ed_contrib@test.com")
    editor_token = await _make_editor(client, "ed_editor@test.com")

    create_resp = await client.post(
        "/api/v1/submissions",
        json={"title": "Review Me", "category": "essay", "body_text": "Content."},
        headers={"Authorization": f"Bearer {contrib_token}"},
    )
    submission_id = create_resp.json()["id"]

    # Submit it
    await client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        headers={"Authorization": f"Bearer {contrib_token}"},
    )

    # Editor moves to under_review
    resp = await client.patch(
        f"/api/v1/editorial/submissions/{submission_id}/status",
        json={"status": "under_review"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "under_review"

    # Editor accepts
    resp = await client.patch(
        f"/api/v1/editorial/submissions/{submission_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_invalid_status_transition(client: AsyncClient) -> None:
    """Invalid status transitions return 400."""
    contrib_token = await _make_contributor(client, "bad_trans@test.com")
    editor_token = await _make_editor(client, "bad_trans_editor@test.com")

    create_resp = await client.post(
        "/api/v1/submissions",
        json={"title": "Bad Transition", "category": "essay", "body_text": "Body."},
        headers={"Authorization": f"Bearer {contrib_token}"},
    )
    submission_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        headers={"Authorization": f"Bearer {contrib_token}"},
    )

    # Try to jump directly from submitted to accepted (skipping under_review)
    resp = await client.patch(
        f"/api/v1/editorial/submissions/{submission_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_publish_submission_creates_article(client: AsyncClient) -> None:
    """Publishing an accepted submission creates an Article."""
    contrib_token = await _make_contributor(client, "pub_contrib@test.com")
    editor_token = await _make_editor(client, "pub_editor@test.com")

    create_resp = await client.post(
        "/api/v1/submissions",
        json={"title": "Publish This Essay", "category": "essay", "body_text": "Full content here."},
        headers={"Authorization": f"Bearer {contrib_token}"},
    )
    submission_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        headers={"Authorization": f"Bearer {contrib_token}"},
    )
    await client.patch(
        f"/api/v1/editorial/submissions/{submission_id}/status",
        json={"status": "under_review"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    await client.patch(
        f"/api/v1/editorial/submissions/{submission_id}/status",
        json={"status": "accepted"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )

    pub_resp = await client.post(
        f"/api/v1/editorial/submissions/{submission_id}/publish",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert pub_resp.status_code == 201
    article = pub_resp.json()
    assert article["status"] == "published"
    assert article["slug"] == "publish-this-essay"
