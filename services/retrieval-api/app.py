# IRIS — Retrieval API (Cloud Run).
# Phase 0.8: hello-world /healthz. Real /search + /query land in Phases 2.0/3.0.

import os

from flask import Flask, jsonify

app = Flask(__name__)

PORT = int(os.environ.get("PORT", 8080))


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "retrieval-api", "phase": "0.8"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
