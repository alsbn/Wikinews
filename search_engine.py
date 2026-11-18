
import re
import sqlite3
from pathlib import Path

DB_FILE = Path("index/wikinews.db")


def build_query(query):
    """
    Converte la query dell'utente in una query FTS5 sicura.

    Tutti i termini sono richiesti (AND).
    La punteggiatura viene ignorata.
    """

    terms = re.findall(r"\w+", query, flags=re.UNICODE)

    if not terms:
        return ""

    return " AND ".join(
        '"' + term.replace('"', '""') + '"'
        for term in terms
    )


def search(query, limit=20, offset=0):
    if not query or not query.strip():
        return []

    if not 1 <= limit <= 100:
        raise ValueError("Limit deve essere compreso tra 1 e 100")

    if offset < 0:
        raise ValueError("Offset non valido")

    fts_query = build_query(query)

    if not fts_query:
        return []

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row

    try:
        results = connection.execute("""
            SELECT
                a.id,
                a.title,
                a.url,
                a.date_modified,
                a.abstract,
                snippet(articles_fts, 2, '<mark>', '</mark>',
                        ' ... ', 35) AS excerpt,
                bm25(
                    articles_fts,
                    5.0,
                    2.0,
                    1.0,
                    1.0
                ) AS score

            FROM articles_fts

            JOIN articles a
                ON a.id = articles_fts.rowid

            WHERE articles_fts MATCH ?

            ORDER BY score ASC

            LIMIT ? OFFSET ?

        """, (fts_query, limit, offset)).fetchall()

        return [dict(row) for row in results]

    finally:
        connection.close()


def count_results(query):
    fts_query = build_query(query)

    if not fts_query:
        return 0

    connection = sqlite3.connect(DB_FILE)

    try:
        row = connection.execute("""
            SELECT COUNT(*)
            FROM articles_fts
            WHERE articles_fts MATCH ?
        """, (fts_query,)).fetchone()

        return row[0]

    finally:
        connection.close()
