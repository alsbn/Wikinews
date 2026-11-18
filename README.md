Wikinews Search

Motore di ricerca full-text per gli articoli di Wikinews in lingua italiana, basato sul dump Wikimedia Enterprise del 20 marzo 2025.

Architettura
Backend: FastAPI.
Database: SQLite.
Motore di ricerca: FTS5.
Ranking: BM25.
Frontend: HTML, CSS e JavaScript.
Test: pytest.
CI: GitHub Actions.
Limiti conosciuti

La ricerca è lessicale e non semantica. Non sono implementati stemming italiano, sinonimi o ricerca vettoriale.

Stato del progetto:
Versione iniziale: 1.0.0

Comandi per avviare tutto il progetto
Dopo aver creato i file, la sequenza di esecuzione sarà:

# 1. Installazione
    pip install -r requirements.txt

# 2. Test automatici (omettere se non funzionano)
    pytest -v

# 3. Importazione
    python indexer.py

# 4. Avvio
    python app.py

Per valutare la qualità della ricerca:
    python benchmark.py
