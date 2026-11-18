
import sqlite3
import pytest

import search_engine


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"

    monkeypatch.setattr(search_engine, "DB_FILE", db)

    connection = sqlite3.connect(db)

    connection.executescript("""
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            date_modified TEXT,
            abstract TEXT,
            body TEXT,
            categories TEXT
        );

        CREATE VIRTUAL TABLE articles_fts
        USING fts5(
            title, abstract, body, categories,
            tokenize='unicode61 remove_diacritics 2'
        );
    """)

    records = [
        (
            1,
            "Belgio: nuovo governo",
            "https://example.org/1",
            "2009-01-01T00:00:00Z",
            "Politica belga",
            "Il governo del Belgio è stato formato.",
            "Europa Politica"
        ),
        (
            2,
            "Calcio: vittoria italiana",
            "https://example.org/2",
            "2010-01-01T00:00:00Z",
            "Sport",
            "La nazionale italiana vince.",
            "Sport"
        ),
        (
            3,
            "Politica europea",
            "https://example.org/3",
            "2011-01-01T00:00:00Z",
            "Il governo europeo",
            "Discussione politica.",
            "Europa"
        )
    ]

    connection.executemany(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?)",
        records
    )

    connection.executemany("""
        INSERT INTO articles_fts
        (rowid, title, abstract, body, categories)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (r[0], r[1], r[4], r[5], r[6])
        for r in records
    ])

    connection.commit()
    connection.close()

    yield db


def test_query_normalization():
    assert search_engine.build_query("Belgio governo") == (
        '"Belgio" AND "governo"'
    )


def test_empty_query():
    assert search_engine.search("") == []


def test_and_semantics(test_db):
    results = search_engine.search("Belgio governo")

    assert len(results) == 1
    assert results[0]["id"] == 1


def test_no_results(test_db):
    assert search_engine.search("astronauta Marte") == []


def test_title_ranking(test_db):
    results = search_engine.search("governo")

    assert results[0]["id"] in (1, 3)


def test_invalid_limit(test_db):
    with pytest.raises(ValueError):
        search_engine.search("governo", limit=0)
