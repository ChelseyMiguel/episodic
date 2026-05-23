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

        # Chelsey Miguel — founder and primary contributor
        contributor1 = User(
            email="contributor1@episodic.org",
            hashed_password=hash_password("contrib123"),
            display_name="Chelsey Miguel",
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
            bio="Chelsey is the founder of Episodic Magazine and a STEM enthusiast from Maui, Hawaiʻi. She writes about living with lupus, navigating high school with a chronic illness, and finding community through words.",
            pronouns="she/her",
            condition_identity="Lupus",
            condition_identity_public=True,
            anonymous_mode=False,
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

        tag_grief = Tag(name="Grief", slug="grief")
        tag_family = Tag(name="Family", slug="family")
        tag_hospital = Tag(name="Hospital", slug="hospital")
        tag_education = Tag(name="Education", slug="education")
        tag_lupus = Tag(name="Lupus", slug="lupus")
        tag_youth = Tag(name="Youth", slug="youth")
        tag_hawaii = Tag(name="Hawaiʻi", slug="hawaii")
        tag_mental_health = Tag(name="Mental Health", slug="mental-health")
        session.add_all([tag_grief, tag_family, tag_hospital, tag_education, tag_lupus, tag_youth, tag_hawaii, tag_mental_health])
        await session.flush()

        article1 = Article(
            title="Bitter Sweet",
            slug="bitter-sweet",
            excerpt="I hear the flare of bad news / From whoever tells the tale",
            body=(
                "<p style='font-style:italic; line-height:2;'>"
                "I hear the flare of bad news<br/>"
                "From whoever tells the tale-<br/>"
                "The sweetness that turns bitter<br/>"
                "Awoken to their chatter<br/>"
                "On a monotone platter<br/>"
                "How can I even bother<br/>"
                "When the sounds of their concern matter?<br/>"
                "Well, what can I do? I can muster nothing but laughter."
                "</p>"
            ),
            category="poetry",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=["chronic illness"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            featured=True,
        )
        article1.tags = [tag_poetry, tag_chronic, tag_grief]
        session.add(article1)

        article2 = Article(
            title="Belated",
            slug="belated",
            excerpt="Somewhere at the beginning of time / I see her face hidden behind a postcard",
            body=(
                "<p style='font-style:italic; line-height:2;'>"
                "Somewhere at the beginning of time<br/>"
                "I see her face hidden behind a postcard<br/>"
                "Her smile before the journeys arrived<br/>"
                "How I wish I was closer<br/>"
                "To take her hand to say she'll be fine<br/>"
                "And soothe her worries in before the night<br/>"
                "\"Shh it will be okay\"<br/>"
                "These words would rhyme when I saw her<br/>"
                "Her softness and laughter<br/>"
                "How I wish I could hold her"
                "</p>"
            ),
            category="poetry",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=["chronic illness", "grief"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
            featured=False,
        )
        article2.tags = [tag_poetry, tag_grief, tag_family]
        session.add(article2)

        article3 = Article(
            title="Aftertaste",
            slug="aftertaste",
            excerpt="All I've ever wanted / Was to see her amongst the toneless walls",
            body=(
                "<p style='font-style:italic; line-height:2;'>"
                "All I've ever wanted<br/>"
                "Was to see her amongst the toneless walls<br/>"
                "Her heart beating faster<br/>"
                "\"Mom! I'm getting taller!\"<br/>"
                "Even amidst those repetitive patterns<br/>"
                "Those flat beds and desks<br/>"
                "Those repeatable beeps and squeaks<br/>"
                "My want becomes stronger<br/>"
                "Even though you are surrounded by bleakness<br/>"
                "I'm unable to comprehend your laughter"
                "</p>"
            ),
            category="poetry",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=["chronic illness", "hospital", "family illness"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
            featured=False,
        )
        article3.tags = [tag_poetry, tag_family, tag_hospital]
        session.add(article3)

        article4 = Article(
            title="The Waiting Room",
            slug="the-waiting-room",
            excerpt="For others, time is persisting / For me, I am still waiting",
            body=(
                "<p style='font-style:italic; line-height:2;'>"
                "For other people patience is not a given<br/>"
                "Patience in my eyes is the bleakness of these never-ending walls<br/>"
                "It's the wonder of lying awake at night with no emotion<br/>"
                "The uncertainty ringing amongst telephone calls<br/>"
                "Ah yes, maybe the crying too,<br/>"
                "And the epoxy coated floors that are blue<br/>"
                "For others, time is persisting<br/>"
                "For me, I am still waiting&#8211;<br/>"
                "Tapping my shoe, biting the blues<br/>"
                "Tracing seams in every fabric through<br/>"
                "Time is a tightening noose<br/>"
                "But patience is lonely<br/>"
                "Can you wait with me too?"
                "</p>"
            ),
            category="poetry",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=["chronic illness", "hospital"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 4, tzinfo=timezone.utc),
            featured=True,
        )
        article4.tags = [tag_poetry, tag_chronic, tag_hospital, tag_grief]
        session.add(article4)

        article5 = Article(
            title="My name is..",
            slug="my-name-is",
            excerpt="It's courageous to share your name / Although the classroom is uniform",
            body=(
                "<p style='font-style:italic; line-height:2;'>"
                "It's courageous to share your name<br/>"
                "Although the classroom is uniform<br/>"
                "And the restless clean clock is whiny<br/>"
                "There even the dimly lit light is mellow<br/>"
                "Everyone stays cuddled sleepy<br/>"
                "Even if I go away<br/>"
                "And dont show my face till the next day<br/>"
                "A part of me still remains<br/>"
                "Why?<br/>"
                "I know all their names<br/>"
                "Amelia likes piano<br/>"
                "Annie likes to cook<br/>"
                "And Bryce likes to read books<br/>"
                "I admit I'm just shy<br/>"
                "But I haven't even said my name<br/>"
                "And sometimes I hope<br/>"
                "That we share each other's pain<br/>"
                "That we all can cry, that we can all blame<br/>"
                "Because amongst those names<br/>"
                "We all face the idea of grimace<br/>"
                "Or even our own demise<br/>"
                "Yet I see within each other's innocent eyes<br/>"
                "That maybe we'll all survive"
                "</p>"
            ),
            category="poetry",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=[],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 5, tzinfo=timezone.utc),
            featured=False,
        )
        article5.tags = [tag_poetry, tag_identity, tag_youth, tag_mental_health]
        session.add(article5)

        article6 = Article(
            title="Students With Chronic Illness Shouldn't Have To Choose Between Health And Education",
            slug="students-chronic-illness-health-education",
            excerpt="No student should have to grieve who they used to be while also fighting to keep up in school.",
            body=(
                "<p class='text-caption text-outline mb-6'>Originally published in <em>Honolulu Civil Beat</em>, 2026.</p>"
                "<p>Time and time again, I find myself haunted by expectations I can no longer meet. "
                "Orderly tasks I cannot single-handedly do independently anymore and haunted by the loss of what could've been.</p>"
                "<p>There's a loss of identity that comes with chronic illness, not just the pain or fatigue, but the loss of your previous self. "
                "I used to be the girl who could sprint effortlessly under the sun, who raised her hand without hesitation, "
                "who attended school and participated everyday. I was curious, driven, and certain of where I was going, "
                "and what I could bring to my future.</p>"
                "<p>I live in the shadow of that version of myself burdened by her bags of expectation.</p>"
                "<p>I was recently diagnosed with lupus, a chronic autoimmune condition. Some days, I can function almost normally. "
                "Other days, flare-ups take that functionality away, my energy, my focus, my ability to show up in the way school expects of me. "
                "I felt like I had to work harder to reach the bare minimum of my peers. "
                "It felt harder to fulfill what I previously found easy in the past.</p>"
                "<p>And it's not just me, there are other students facing these challenges. "
                "Our education system is not built for unpredictability. "
                "It expects consistency: consistent attendance, consistent productivity, consistent performance and participation. "
                "But for students like me, consistency is not a given option we can consider.</p>"
                "<p>Federal protections like Section 504 exist to support students with disabilities. "
                "But in practice, the support for chronic and episodic conditions, especially those that fluctuate, is often inconsistent. "
                "Some teachers understand. Some systems adapt and others don't.</p>"
                "<p>We fall behind not because we are incapable, but because we are navigating conditions that fluctuate and feel invisible to the naked eye. "
                "Sometimes feeling unsupported and misunderstood about our condition.</p>"
                "<p>In Hawaiʻi, this issue carries more impact for our students. "
                "Autoimmune conditions like lupus are more prevalent among Native Hawaiian, Pacific Islander, and Asian populations, "
                "which affects the majority of our population.</p>"
                "<p>This legislative session, I worked with the Department of Education to further adapt Section 504 to accommodate flare-ups "
                "and helped draft a resolution encouraging clearer guidance and more consistent support for students with chronic illness. "
                "Even without immediate policy change, the conversations this effort sparked matter towards these issues and support for our students.</p>"
                "<p>Because what students like me need is not pity or lowered expectations. We need an understanding of us. "
                "We need flexibility. We need consistency in the support that we need in class. "
                "No student should have to grieve who they used to be while also fighting to keep up in school "
                "and no student should have to choose between their health and their education.</p>"
            ),
            category="op_ed",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=["chronic illness", "lupus"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 6, tzinfo=timezone.utc),
            featured=True,
        )
        article6.tags = [tag_chronic, tag_lupus, tag_education, tag_hawaii, tag_advocacy]
        session.add(article6)

        article7 = Article(
            title="Things That Helped Me With Lupus",
            slug="things-that-helped-me-with-lupus",
            excerpt="I am writing this to provide general tips on how to mentally survive through it all and reclaim a sense of agency over your own well-being.",
            body=(
                "<p><em>Note: I am not a medically trained professional.</em></p>"
                "<p>As someone who's constantly fighting Systemic Lupus, I understand the severity of what more than a million face "
                "in their day-to-day lives, and how our condition plays a complex and multifaceted role within our relationships and "
                "ongoing connections. For me, it was hard to endure the struggle of performing the needed expectations in school, "
                "and that played a critical aspect on who I am today. I am writing this as a means to provide general tips on how to "
                "mentally survive through it all and reclaim a sense of agency over your own well-being.</p>"

                "<h3>Get enough sleep</h3>"
                "<p>For me, sleep was not a given mandatory. I persisted with completing any missing assignments for the sole purpose "
                "of maintaining my grade. Little did I know, I wasn't letting my body properly consolidate memory. "
                "I was unintentionally worsening my performance in school, easily forgetting things and saw a declining score in my tests. "
                "When I visited my rheumatologist, he told me that it was brain fog, and that sleeping more was the only way to give my "
                "neurological system the recovery time it needed from all the stress and fatigue.</p>"

                "<h3>Set realistic boundaries</h3>"
                "<p>I used to feel guilty for saying no to social events or extra projects, to prove that I can achieve everything, "
                "but I learned that \"pushing through\" usually led to a flare-up that sidelined me with fatigue for a week. "
                "Now, I protect my energy like a limited resource, and think carefully about what I should invest my time and energy in. "
                "I've found that the people who truly care about me respect those boundaries, and I've gotten more time to relax from all the stress.</p>"

                "<h3>Practice self-compassion</h3>"
                "<p>On days when the fatigue is overwhelming, it's easy to fall into a cycle of self-blame and regret. "
                "What I did was learn how to treat myself with the same kindness and tenderness I would offer a friend. "
                "Acknowledging that your body is fighting a battle every day makes it easier to forgive yourself for the things you didn't get done, "
                "and that you don't need to earn a break, you already deserve one.</p>"

                "<h3>Celebrate small wins</h3>"
                "<p>Somedays, we all are in bad shape to consistently produce quality work and lose motivation because of fatigue and mood. "
                "What I did to combat this was to celebrate myself for doing something simple like checking emails or just taking a nap. "
                "Whatever it was, I'd just list them off my checklist and feel content. "
                "It's not always the big things, but the actions that matter.</p>"
            ),
            category="essay",
            contributor_id=contributor1.id,
            anonymous_byline=False,
            byline_name="Chelsey Miguel",
            issue_id=issue.id,
            content_warnings=["chronic illness", "lupus"],
            status=ArticleStatus.published,
            published_at=datetime(2026, 5, 7, tzinfo=timezone.utc),
            featured=False,
        )
        article7.tags = [tag_chronic, tag_lupus, tag_mental_health, tag_identity]
        session.add(article7)

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
