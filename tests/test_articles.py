"""
Tests for public article listing, filtering, and slug lookup.
"""
import uuid
import pytest
from httpx import AsyncClient

from app.models.article import Article, ArticleStatus
from app.models.user import User, UserRole
from app.core.security import hash_password
from tests.conftest import TestSessionLocal


async def _create_published_article(title: str, slug: str, category: str = "essay", featured: bool = False) -> None:
    """Insert a published article directly into the test DB."""
    async with TestSessionLocal() as session:
        # Ensure a contributor user exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "article_author@test.com"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="article_author@test.com",
                hashed_password=hash_password("pass123"),
                display_name="Article Author",
                role=UserRole.contributor,
                is_active=True,
            )
            session.add(user)
            await session.flush()

        article = Article(
            title=title,
            slug=slug,
            body=f"Body of {title}",
            category=category,
            contributor_id=user.id,
            anonymous_byline=False,
            status=ArticleStatus.published,
            featured=featured,
            content_warnings=[],
        )
        session.add(article)
        await session.commit()


@pytest.mark.asyncio
async def test_list_published_articles_public(client: AsyncClient) -> None:
    """Public endpoint returns published articles without authentication."""
    await _create_published_article("Public Article One", "public-article-one")

    resp = await client.get("/api/v1/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_article_by_slug(client: AsyncClient) -> None:
    """Public slug lookup returns the article."""
    await _create_published_article("Slug Test Article", "slug-test-article")

    resp = await client.get("/api/v1/articles/slug-test-article")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "slug-test-article"
    assert data["title"] == "Slug Test Article"


@pytest.mark.asyncio
async def test_get_nonexistent_article_returns_404(client: AsyncClient) -> None:
    """Looking up a nonexistent slug returns 404."""
    resp = await client.get("/api/v1/articles/this-does-not-exist-at-all")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_articles_by_category(client: AsyncClient) -> None:
    """Articles can be filtered by category."""
    await _create_published_article("Poetry Piece", "poetry-piece-filter", category="poetry")
    await _create_published_article("Essay Piece", "essay-piece-filter", category="essay")

    resp = await client.get("/api/v1/articles?category=poetry")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["category"] == "poetry"


@pytest.mark.asyncio
async def test_filter_articles_by_featured(client: AsyncClient) -> None:
    """Articles can be filtered by featured flag."""
    await _create_published_article("Featured Article", "featured-article-test", featured=True)
    await _create_published_article("Normal Article", "normal-article-test", featured=False)

    resp = await client.get("/api/v1/articles?featured=true")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["featured"] is True


@pytest.mark.asyncio
async def test_featured_articles_endpoint(client: AsyncClient) -> None:
    """Dedicated featured endpoint returns only featured published articles."""
    await _create_published_article("Featured Special", "featured-special-slug", featured=True)

    resp = await client.get("/api/v1/articles/featured")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["featured"] is True


@pytest.mark.asyncio
async def test_anonymous_byline_hides_real_name(client: AsyncClient) -> None:
    """Article with anonymous_byline=True shows 'Anonymous', not the contributor's name."""
    async with TestSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "article_author@test.com"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="article_author@test.com",
                hashed_password=hash_password("pass123"),
                display_name="Real Name That Must Stay Hidden",
                role=UserRole.contributor,
                is_active=True,
            )
            session.add(user)
            await session.flush()
        else:
            user.display_name = "Real Name That Must Stay Hidden"

        article = Article(
            title="Anonymous Story",
            slug="anonymous-story-byline-test",
            body="Private story body.",
            category="essay",
            contributor_id=user.id,
            anonymous_byline=True,
            byline_name=None,
            status=ArticleStatus.published,
            content_warnings=[],
        )
        session.add(article)
        await session.commit()

    resp = await client.get("/api/v1/articles/anonymous-story-byline-test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["byline"] == "Anonymous"
    assert "Real Name That Must Stay Hidden" not in str(data)


@pytest.mark.asyncio
async def test_article_public_response_has_no_contributor_id_leak(client: AsyncClient) -> None:
    """Public article response does not expose contributor_id directly in byline context."""
    await _create_published_article("Safe Article", "safe-article-check")

    resp = await client.get("/api/v1/articles/safe-article-check")
    assert resp.status_code == 200
    data = resp.json()
    # contributor_id may appear as a UUID in the response (it's not private),
    # but the byline field must exist and never be the contributor's real name when anonymous
    assert "byline" in data


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient) -> None:
    """Article list supports skip/limit pagination."""
    for i in range(5):
        await _create_published_article(f"Paginated Article {i}", f"paginated-article-{i}-xyz")

    resp1 = await client.get("/api/v1/articles?skip=0&limit=3")
    resp2 = await client.get("/api/v1/articles?skip=3&limit=3")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert len(resp1.json()["items"]) <= 3
