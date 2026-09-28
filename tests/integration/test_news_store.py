from datetime import UTC, datetime, timedelta

from packages.common.db.models import NewsEventRecord
from packages.common.schemas import NewsEvent, NewsEventCategory
from packages.ingestion.store import persist_news_article, persist_news_event


def _event(confidence=0.9, relevance=0.8) -> NewsEvent:
    return NewsEvent(
        event="Hormuz escalation",
        category=NewsEventCategory.MIDDLE_EAST,
        entities=["Iran"],
        direct_assets=["Brent"],
        transmission_chain=["oil_up", "gold_down"],
        relevance=relevance,
        confidence=confidence,
        rationale="Oil supply risk.",
    )


def test_persist_article_deduplicates_on_headline_and_date(db):
    published_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    a1 = persist_news_article(
        db, source="Reuters", headline="Iran threatens Hormuz closure", body=None, url=None,
        published_at=published_at,
    )
    a2 = persist_news_article(
        db, source="Bloomberg", headline="IRAN THREATENS HORMUZ CLOSURE", body=None, url=None,
        published_at=published_at + timedelta(hours=3),
    )
    db.commit()
    assert a1.id == a2.id


def test_persist_article_sets_source_tier(db):
    article = persist_news_article(
        db, source="Reuters", headline="Fed hikes rates", body=None, url=None,
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
    )
    db.commit()
    assert article.source_tier == 1

    article2 = persist_news_article(
        db, source="Some Random Blog", headline="Gold is going to the moon", body=None, url=None,
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
    )
    db.commit()
    assert article2.source_tier == 3


def test_persist_event_caps_confidence_to_source_tier(db):
    article = persist_news_article(
        db, source="Some Random Blog", headline="Gold is going to the moon", body=None, url=None,
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
    )
    db.commit()

    record = persist_news_event(db, article=article, event=_event(confidence=0.95), model="claude-opus-5")
    db.commit()

    assert record.confidence == 0.55  # tier-3 ceiling, not the model's raw 0.95
    stored = db.get(NewsEventRecord, record.id)
    assert stored.event == "Hormuz escalation"
    assert stored.transmission_chain == ["oil_up", "gold_down"]


def test_persist_event_tier1_source_keeps_high_confidence(db):
    article = persist_news_article(
        db, source="Reuters", headline="Iran threatens Hormuz closure", body=None, url=None,
        published_at=datetime(2026, 6, 5, tzinfo=UTC),
    )
    db.commit()
    record = persist_news_event(db, article=article, event=_event(confidence=0.9), model="claude-opus-5")
    db.commit()
    assert record.confidence == 0.9
