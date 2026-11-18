
from indexer import parse_article, extract_html


def make_article():
    return {
        "name": "Belgio: finalmente varato il nuovo governo",
        "identifier": 19405,
        "abstract": "Notizia sul nuovo governo belga.",
        "date_modified": "2009-10-16T22:33:23Z",
        "url": "https://it.wikinews.org/wiki/Belgio",
        "namespace": {"identifier": 0},
        "categories": [
            {"name": "Categoria:Belgio"},
            {"name": "Categoria:Politica"}
        ],
        "article_body": {
            "html": "<p>Il nuovo governo del Belgio.</p>"
        }
    }


def test_parse_article():
    result = parse_article(make_article())

    assert result is not None
    assert result[0] == 19405
    assert result[1] == "Belgio: finalmente varato il nuovo governo"
    assert "Belgio" in result[5]


def test_ignore_non_article():
    article = make_article()
    article["namespace"]["identifier"] = 1

    assert parse_article(article) is None


def test_ignore_article_after_cutoff():
    article = make_article()
    article["date_modified"] = "2025-03-21T10:00:00Z"

    assert parse_article(article) is None


def test_extract_html():
    html = """
    <html>
      <body>
        <p>Notizia <b>importante</b></p>
        <script>codice non indicizzato</script>
      </body>
    </html>
    """

    result = extract_html(html)

    assert "Notizia" in result
    assert "importante" in result
    assert "codice non indicizzato" not in result


def test_missing_content():
    article = make_article()
    article.pop("article_body")

    result = parse_article(article)

    assert result is not None
    assert result[5] == ""
