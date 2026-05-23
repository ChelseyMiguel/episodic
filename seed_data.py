"""
Seed data script for Episodic.

Creates tables and populates the database with sample data for development.

Usage:
    python seed_data.py
"""
import asyncio
from datetime import datetime, timezone, date

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.database import Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.contributor import ContributorProfile, ContributorStatus
from app.models.issue import Issue, IssueStatus
from app.models.article import Article, Tag, ArticleStatus
from app.models.resource import Resource, ResourceCategory, ResourceRegion
from app.models.submission import Submission, EditorialNote, SubmissionCategory, SubmissionStatus
from app.models.newsletter import NewsletterSubscriber


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        print("Seeding users...")

        admin = User(
            email="admin@episodic.org",
            hashed_password=hash_password("admin123"),
            display_name="Episodic Admin",
            role=UserRole.admin,
            is_active=True,
            is_email_verified=True,
        )
        session.add(admin)

        editor = User(
            email="editor@episodic.org",
            hashed_password=hash_password("editor123"),
            display_name="Episodic Editor",
            role=UserRole.editor,
            is_active=True,
            is_email_verified=True,
        )
        session.add(editor)

        # Generic contributor accounts — no real names
        contributor1 = User(
            email="contributor1@episodic.org",
            hashed_password=hash_password("contrib123"),
            display_name="Anonymous Contributor",
            role=UserRole.contributor,
            is_active=True,
            is_email_verified=True,
        )
        session.add(contributor1)

        contributor2 = User(
            email="contributor2@episodic.org",
            hashed_password=hash_password("contrib123"),
            display_name="Anonymous Contributor",
            role=UserRole.contributor,
            is_active=True,
            is_email_verified=True,
        )
        session.add(contributor2)

        reader = User(
            email="reader@episodic.org",
            hashed_password=hash_password("reader123"),
            display_name="Reader",
            role=UserRole.reader,
            is_active=True,
            is_email_verified=True,
        )
        session.add(reader)

        await session.flush()
        print("Users created.")

        print("Seeding contributor profiles...")

        profile1 = ContributorProfile(
            user_id=contributor1.id,
            bio="A writer living with chronic illness.",
            pronouns=None,
            condition_identity=None,
            condition_identity_public=False,
            anonymous_mode=True,
            portfolio_url=None,
            social_links={},
            status=ContributorStatus.approved,
        )
        session.add(profile1)

        profile2 = ContributorProfile(
            user_id=contributor2.id,
            bio="A writer and advocate.",
            pronouns=None,
            condition_identity=None,
            condition_identity_public=False,
            anonymous_mode=True,
            portfolio_url=None,
            social_links={},
            status=ContributorStatus.approved,
        )
        session.add(profile2)

        await session.flush()
        print("Contributor profiles created.")

        print("Seeding issue...")

        issue = Issue(
            title="Invisible Symptoms",
            slug="invisible-symptoms",
            theme_description=(
                "Our inaugural issue explores the invisible dimensions of chronic illness "
                "and disability — the symptoms others can't see, the grief of before and after, "
                "and the small victories that never make it into a doctor's notes. "
                "Submissions open now."
            ),
            editors_letter=(
                "Welcome to Episodic. This is a space built for and by young people living with "
                "chronic illness and disability. Every piece in these pages represents an act of "
                "courage. We are honored you are here."
            ),
            cover_image_metadata={
                "storage_key": None,
                "alt_text": "Abstract watercolor in soft earth tones",
                "caption": "Cover art by a contributor who wishes to remain anonymous",
            },
            submission_deadline=datetime(2026, 8, 1, tzinfo=timezone.utc),
            publication_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
            status=IssueStatus.published,
        )
        session.add(issue)
        await session.flush()
        print("Issue created.")

        print("Seeding tags...")

        tag_chronic = Tag(name="Chronic Illness", slug="chronic-illness")
        tag_disability = Tag(name="Disability", slug="disability")
        tag_advocacy = Tag(name="Advocacy", slug="advocacy")
        tag_poetry = Tag(name="Poetry", slug="poetry")
        tag_identity = Tag(name="Identity", slug="identity")
        session.add_all([tag_chronic, tag_disability, tag_advocacy, tag_poetry, tag_identity])
        await session.flush()
        print("Tags created.")

        print("Seeding articles...")

        article1 = Article(
            title="The Exhaustion No One Sees",
            slug="the-exhaustion-no-one-sees",
            excerpt="Fatigue is not tiredness. It is a wall you run into before you even get out of bed.",
            body=(
                "<p>Fatigue is not tiredness. Tiredness means you slept poorly and need a nap. "
                "Fatigue means that before you've gotten out of bed, you've already used up half "
                "of everything you have to give for the day.</p>"
                "<p>I've tried to explain this to teachers, to friends, to my own family. "
                "The words never quite land. 'But you don't look sick,' they say. I know. "
                "That's the point.</p>"
                "<p>Invisible symptoms are not invisible to us. We just learn to make them "
                "invisible to you because the alternative — your pity, your disbelief, your "
                "unsolicited advice — costs more energy than we have.</p>"
                "<p><em>This is a placeholder essay. We are currently accepting submissions for "
                "our inaugural issue. If this resonates with you, we'd love to read your story.</em></p>"
            ),
            category="essay",
            contributor_id=contributor1.id,
            anonymous_byline=True,
            byline_name="Anonymous",
            issue_id=issue.id,
            content_warnings=["chronic illness", "fatigue"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            featured=True,
        )
        article1.tags = [tag_chronic]
        session.add(article1)

        article2 = Article(
            title="A Letter to My IEP Committee",
            slug="a-letter-to-my-iep-committee",
            excerpt="You have the power to make school survivable. Please use it.",
            body=(
                "<p>To the people sitting around the table deciding what accommodations I deserve:</p>"
                "<p>I know you're tired. I know you have thirty other students. "
                "I know this process is bureaucratic and exhausting for everyone involved. "
                "I know.</p>"
                "<p>But I need you to know something too: I have been preparing for this meeting "
                "for weeks. I have written down everything I wanted to say and practiced it "
                "in the mirror. I have brought documentation that my doctor spent three appointments "
                "helping me fill out.</p>"
                "<p>I am not here to be difficult. I am here because I want to learn, "
                "and I need your help to do that. Please let me.</p>"
                "<p><em>This is a placeholder piece. Episodic is currently accepting submissions. "
                "Write to us.</em></p>"
            ),
            category="op_ed",
            contributor_id=contributor2.id,
            anonymous_byline=True,
            byline_name="Anonymous",
            issue_id=issue.id,
            content_warnings=["disability rights", "education"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            featured=False,
        )
        article2.tags = [tag_disability, tag_advocacy]
        session.add(article2)

        article3 = Article(
            title="Still",
            slug="still",
            excerpt="Some days the body is the room / and the room is everything.",
            body=(
                "<p><em>Some days the body is the room</em><br/>"
                "<em>and the room is everything.</em></p>"
                "<p><em>The ceiling learns your name.</em><br/>"
                "<em>The light moves and you do not.</em></p>"
                "<p><em>This is not giving up.</em><br/>"
                "<em>This is surviving at the speed your body allows.</em></p>"
                "<p><em>This is a placeholder poem. Episodic is currently accepting poetry submissions.</em></p>"
            ),
            category="poetry",
            contributor_id=contributor1.id,
            anonymous_byline=True,
            byline_name="Anonymous",
            issue_id=issue.id,
            content_warnings=[],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            featured=False,
        )
        article3.tags = [tag_poetry, tag_chronic]
        session.add(article3)

        await session.flush()
        print("Articles created.")

        print("Seeding resources...")

        resource_global = Resource(
            title="The Chronic Illness Support Network",
            description="A global peer support network for people of all ages living with chronic illness. Offers forums, mentorship matching, and a resource library.",
            category=ResourceCategory.chronic_illness,
            external_link="https://cisnetwork.example.org",
            region=ResourceRegion.global_,
            reviewed_by_editor=True,
            last_reviewed_at=date(2025, 8, 1),
            is_hidden=False,
            created_by=editor.id,
        )
        session.add(resource_global)

        resource_us = Resource(
            title="Disability Rights Advocates (DRA)",
            description="Nonprofit legal center dedicated to advancing the rights and opportunities of people with disabilities through high-impact litigation.",
            category=ResourceCategory.disability_rights,
            external_link="https://dralegal.org",
            region=ResourceRegion.US,
            reviewed_by_editor=True,
            last_reviewed_at=date(2025, 7, 15),
            is_hidden=False,
            created_by=editor.id,
        )
        session.add(resource_us)

        await session.flush()
        print("Resources created.")

        print("Seeding newsletter subscribers...")

        subscriber = NewsletterSubscriber(
            email="newsletter@example.com",
            is_confirmed=True,
            confirmation_token=None,
            subscribed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        session.add(subscriber)

        await session.commit()
        print("\n=== Seed data complete ===")
        print("Admin:       admin@episodic.org / admin123")
        print("Editor:      editor@episodic.org / editor123")
        print("Contributor: contributor1@episodic.org / contrib123")
        print("Reader:      reader@episodic.org / reader123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
