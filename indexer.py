
import json
import sqlite3
import tarfile
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DUMP_URL = (
    "https://dumps.wikimedia.org/other/enterprise_html/"
    "runs/20250320/"
    "itwikinews-NS0-20250320-ENTERPRISE-HTML.json.tar.gz"
)

CUTOFF = "2025-03-20T23:59:59Z"

DATA_DIR = Path("data")
INDEX_DIR = Path("index")
DUMP_FILE = DATA_DIR / "wikinews.tar.gz"
DB_FILE = INDEX_DIR / "wikinews.db"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag in ("script", "style", "noscript"):
            self.hidden_depth += 1

        if tag in ("p", "br", "div", "li", "h1", "h2"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.hidden_depth = max(0, self.hidden_depth - 1)

        if tag in ("p", "br", "div", "li"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)

    def get_text(self):
        return " ".join(" ".join(self.parts).split())


def extract_html(html):
    parser = TextExtractor()
    parser.feed(html or "")
    return parser.get_text()


def download_dump():
    DATA_DIR.mkdir(exist_ok=True)
    INDEX_DIR.mkdir(exist_ok=True)

    if DUMP_FILE.exists():
        print("Dump già scaricato.")
        return

    print("Download del dump...")

    request = urllib.request.Request(
        DUMP_URL,
        headers={"User-Agent": "WikinewsSearch/1.0"}
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        with open(DUMP_FILE, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

    print("Download completato.")


def create_database(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            date_modified TEXT,
            abstract TEXT,
            body TEXT,
            categories TEXT
        )
    """)

    connection.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
        USING fts5(
            title,
            abstract,
            body,
            categories,
            content='articles',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        )
    """)

    # Mantiene sincronizzato l'indice full-text con la tabella.
    connection.executescript("""
        CREATE TRIGGER IF NOT EXISTS articles_ai
        AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(
                rowid, title, abstract, body, categories
            )
            VALUES (
                new.id, new.title, new.abstract,
                new.body, new.categories
            );
        END;

        CREATE TRIGGER IF NOT EXISTS articles_ad
        AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(
                articles_fts, rowid, title,
                abstract, body, categories
            )
            VALUES (
                'delete', old.id, old.title,
                old.abstract, old.body, old.categories
            );
        END;

        CREATE TRIGGER IF NOT EXISTS articles_au
        AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(
                articles_fts, rowid, title,
                abstract, body, categories
            )
            VALUES (
                'delete', old.id, old.title,
                old.abstract, old.body, old.categories
            );

            INSERT INTO articles_fts(
                rowid, title, abstract, body, categories
            )
            VALUES (
                new.id, new.title, new.abstract,
                new.body, new.categories
            );
        END;
    """)

    connection.commit()


def parse_article(article):
    namespace = article.get("namespace", {}).get("identifier")

    if namespace != 0:
        return None

    modified = article.get("date_modified")

    if not modified or modified[:10] > CUTOFF[:10]:
        return None

    title = article.get("name", "").strip()

    if not title:
        return None

    abstract = article.get("abstract") or ""

    article_body = article.get("article_body") or {}
    body = extract_html(article_body.get("html", ""))

    if not body:
        body = article_body.get("wikitext", "")

    categories = " ".join(
        category.get("name", "")
        for category in article.get("categories", [])
    )

    return (
        article.get("identifier"),
        title,
        article.get("url", ""),
        modified,
        abstract,
        body,
        categories
    )


def import_dump():
    download_dump()

    connection = sqlite3.connect(DB_FILE)
    create_database(connection)

    inserted = 0
    skipped = 0
    batch = []

    print("Lettura del dump...")

    with tarfile.open(DUMP_FILE, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue

            extracted = archive.extractfile(member)

            if extracted is None:
                continue

            for line in extracted:
                if not line.strip():
                    continue

                try:
                    article = json.loads(line)
                    record = parse_article(article)

                    if record is not None:
                        batch.append(record)
                    else:
                        skipped += 1

                except (json.JSONDecodeError, TypeError, ValueError):
                    skipped += 1

                if len(batch) >= 500:
                    save_batch(connection, batch)
                    inserted += len(batch)
                    batch.clear()

                    print(f"Indicizzati: {inserted}")

    if batch:
        save_batch(connection, batch)
        inserted += len(batch)

    connection.execute("INSERT INTO articles_fts(articles_fts) VALUES('optimize')")
    connection.commit()
    connection.close()

    print(f"Indicizzazione completata: {inserted} articoli.")
    print(f"Record esclusi: {skipped}")


def save_batch(connection, batch):
    connection.executemany("""
        INSERT OR REPLACE INTO articles
        (id, title, url, date_modified, abstract, body, categories)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, batch)

    connection.commit()


if __name__ == "__main__":
    import_dump()
