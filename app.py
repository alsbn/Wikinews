
from flask import Flask, render_template, request, jsonify
from search_engine import search, count_results

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()

    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))

        if len(query) > 300:
            return jsonify({"error": "Query troppo lunga"}), 400

        if not 1 <= limit <= 100 or offset < 0:
            return jsonify({"error": "Parametri non validi"}), 400

        results = search(query, limit, offset)

        return jsonify({
            "query": query,
            "total": count_results(query),
            "results": results
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
