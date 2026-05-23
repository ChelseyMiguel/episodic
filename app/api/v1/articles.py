"""
Article endpoints.
Public endpoints return ArticlePublic (safe byline, no internal fields).
Editor+ endpoints return ArticleInternal.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.core.permissions import assert_editor, is_editor_or_above
from app.models.article import Article, ArticleStatus, Tag
from app.models.user import User
from app.schemas.article import (
    ArticleCreate,
    ArticleInternal,
    ArticleListResponse,
    ArticlePublic,
    ArticleUpdate,
    FeatureToggleRequest,
    TagSchema,
)
from app.utils.sanitize import sanitize_html, sanitize_plain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["Articles"])


def _build_article_public(article: Article) -> ArticlePublic:
    """Convert Article ORM to ArticlePublic schema with safe byline."""
    if article.anonymous_byline:
        byline = article.byline_name or "Anonymous"
    else:
        byline = article.contributor.display_name if article.contributor else "Unknown"

    return ArticlePublic(
        id=article.id,
        title=article.title,
        slug=article.slug,
        excerpt=article.excerpt,
        body=article.body,
        category=article.category,
        byline=byline,
        anonymous_byline=article.anonymous_byline,
        issue_id=article.issue_id,
        content_warnings=article.content_warnings,
        status=article.status,
        published_at=article.published_at,
        featured=article.featured,
        tags=[TagSchema.model_validate(t) for t in article.tags],
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _build_article_internal(article: Article) -> ArticleInternal:
    """Convert Article ORM to ArticleInternal schema."""
    if article.anonymous_byline:
        byline = article.byline_name or "Anonymous"
    else:
        byline = article.contributor.display_name if article.contributor else "Unknown"

    return ArticleInternal(
        id=article.id,
        submission_id=article.submission_id,
        title=article.title,
        slug=article.slug,
        excerpt=article.excerpt,
        body=article.body,
        category=article.category,
        contributor_id=article.contributor_id,
        byline=byline,
        anonymous_byline=article.anonymous_byline,
        byline_name=article.byline_name,
        issue_id=article.issue_id,
        content_warnings=article.content_warnings,
        status=article.status,
        published_at=article.published_at,
        scheduled_for=article.scheduled_for,
        featured=article.featured,
        tags=[TagSchema.model_validate(t) for t in article.tags],
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


@router.get("/featured", response_model=ArticleListResponse)
async def list_featured_articles(
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """List featured published articles (public)."""
    result = await db.execute(
        select(Article)
        .where(
            Article.status == ArticleStatus.published,
            Article.featured.is_(True),
        )
        .options(selectinload(Article.tags), selectinload(Article.contributor))
        .order_by(Article.published_at.desc())
        .limit(20)
    )
    articles = result.scalars().all()

    return ArticleListResponse(
        items=[_build_article_public(a) for a in articles],
        total=len(articles),
    )


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    skip: int = 0,
    limit: int = 50,
    category: str | None = None,
    tag: str | None = None,
    issue_id: uuid.UUID | None = None,
    featured: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """List published articles with optional filters (public)."""
    query = (
        select(Article)
        .where(Article.status == ArticleStatus.published)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    count_query = select(func.count()).select_from(Article).where(
        Article.status == ArticleStatus.published
    )

    if category:
        query = query.where(Article.category == category)
        count_query = count_query.where(Article.category == category)
    if issue_id:
        query = query.where(Article.issue_id == issue_id)
        count_query = count_query.where(Article.issue_id == issue_id)
    if featured is not None:
        query = query.where(Article.featured == featured)
        count_query = count_query.where(Article.featured == featured)
    if tag:
        query = query.join(Article.tags).where(Tag.slug == tag)
        count_query = count_query.join(Article.tags, isouter=True).where(Tag.slug == tag)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Article.published_at.desc()).offset(skip).limit(limit)
    )
    articles = result.scalars().all()

    return ArticleListResponse(
        items=[_build_article_public(a) for a in articles],
        total=total,
    )


@router.get("/{slug}", response_model=ArticlePublic)
async def get_article_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ArticlePublic:
    """Get a published article by slug (public)."""
    result = await db.execute(
        select(Article)
        .where(Article.slug == slug, Article.status == ArticleStatus.published)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found."
        )

    return _build_article_public(article)


@router.post("", response_model=ArticleInternal, status_code=status.HTTP_201_CREATED)
async def create_article(
    body: ArticleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleInternal:
    """Manually create an article (editor+ only)."""
    assert_editor(current_user)

    base_slug = slugify(body.title)
    slug = base_slug
    counter = 1
    while True:
        existing = await db.execute(select(Article).where(Article.slug == slug))
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    tags: list[Tag] = []
    if body.tag_ids:
        for tag_id in body.tag_ids:
            tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
            tag = tag_result.scalar_one_or_none()
            if tag:
                tags.append(tag)

    article = Article(
        title=sanitize_plain(body.title),
        slug=slug,
        excerpt=sanitize_plain(body.excerpt),
        body=sanitize_html(body.body),
        category=body.category.value,
        contributor_id=body.contributor_id,
        anonymous_byline=body.anonymous_byline,
        byline_name=body.byline_name,
        issue_id=body.issue_id,
        content_warnings=body.content_warnings or [],
        status=body.status,
        scheduled_for=body.scheduled_for,
        featured=body.featured,
        published_at=datetime.now(timezone.utc) if body.status == ArticleStatus.published else None,
    )
    article.tags = tags
    db.add(article)
    await db.flush()
    await db.refresh(article)

    # Reload with relationships
    result = await db.execute(
        select(Article)
        .where(Article.id == article.id)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    article = result.scalar_one()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Article created manually: id={article.id} by editor={current_user.id}"
    )

    return _build_article_internal(article)


@router.patch("/{article_id}", response_model=ArticleInternal)
async def update_article(
    article_id: uuid.UUID,
    body: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleInternal:
    """Update an article (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found."
        )

    if body.title is not None:
        article.title = sanitize_plain(body.title)
    if body.body is not None:
        article.body = sanitize_html(body.body)
    if body.excerpt is not None:
        article.excerpt = sanitize_plain(body.excerpt)
    if body.category is not None:
        article.category = body.category.value
    if body.anonymous_byline is not None:
        article.anonymous_byline = body.anonymous_byline
    if body.byline_name is not None:
        article.byline_name = body.byline_name
    if body.issue_id is not None:
        article.issue_id = body.issue_id
    if body.content_warnings is not None:
        article.content_warnings = body.content_warnings
    if body.status is not None:
        if body.status == ArticleStatus.published and article.status != ArticleStatus.published:
            article.published_at = datetime.now(timezone.utc)
        article.status = body.status
    if body.scheduled_for is not None:
        article.scheduled_for = body.scheduled_for
    if body.featured is not None:
        article.featured = body.featured
    if body.tag_ids is not None:
        tags = []
        for tag_id in body.tag_ids:
            tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
            tag = tag_result.scalar_one_or_none()
            if tag:
                tags.append(tag)
        article.tags = tags

    await db.flush()
    await db.refresh(article)

    # Reload with relationships
    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    article = result.scalar_one()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Article updated: id={article_id} by editor={current_user.id}"
    )

    return _build_article_internal(article)


@router.patch("/{article_id}/feature", response_model=ArticleInternal)
async def toggle_featured(
    article_id: uuid.UUID,
    body: FeatureToggleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArticleInternal:
    """Toggle the featured flag on an article (editor+ only)."""
    assert_editor(current_user)

    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found."
        )

    article.featured = body.featured
    await db.flush()
    await db.refresh(article)

    result = await db.execute(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.tags), selectinload(Article.contributor))
    )
    article = result.scalar_one()

    logger.info(
        f"[{datetime.now(timezone.utc).isoformat()}] Article feature toggled: id={article_id} featured={body.featured}"
    )

    return _build_article_internal(article)
