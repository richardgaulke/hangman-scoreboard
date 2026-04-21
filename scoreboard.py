import os
import secrets
from collections import deque
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request

MAX_HISTORY = 20
scores = {"wins": 0, "losses": 0}
history: deque = deque(maxlen=MAX_HISTORY)

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Hangman Scoreboard</title>
  <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #090b10;
      color: #c8d6e5;
      font-family: 'Share Tech Mono', monospace;
      min-height: 100vh;
      padding: 2rem 1rem;
      background-image:
        linear-gradient(rgba(0,255,180,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,180,0.03) 1px, transparent 1px);
      background-size: 40px 40px;
    }

    header {
      text-align: center;
      margin-bottom: 2rem;
    }

    header h1 {
      font-family: 'Orbitron', sans-serif;
      font-size: 1.6rem;
      letter-spacing: 0.2em;
      color: #00ffb4;
      text-shadow: 0 0 20px #00ffb466;
      text-transform: uppercase;
    }

    header p {
      font-size: 0.75rem;
      color: #4a6080;
      margin-top: 0.4rem;
      letter-spacing: 0.15em;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      max-width: 700px;
      margin: 0 auto 2rem;
    }

    .stat-card {
      background: #0d1117;
      border: 1px solid #00ffb422;
      border-radius: 8px;
      padding: 1.25rem 1rem;
      text-align: center;
      position: relative;
    }

    .corner {
      position: absolute;
      width: 8px;
      height: 8px;
      border-color: #00ffb4;
      border-style: solid;
      opacity: 0.4;
    }
    .corner.tl { top: 6px; left: 6px;   border-width: 1px 0 0 1px; }
    .corner.tr { top: 6px; right: 6px;  border-width: 1px 1px 0 0; }
    .corner.bl { bottom: 6px; left: 6px;  border-width: 0 0 1px 1px; }
    .corner.br { bottom: 6px; right: 6px; border-width: 0 1px 1px 0; }

    .stat-label {
      font-family: 'Orbitron', sans-serif;
      font-size: 0.6rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: #00ffb4;
      opacity: 0.7;
      margin-bottom: 0.5rem;
    }

    .stat-value {
      font-family: 'Orbitron', sans-serif;
      font-size: 2.8rem;
      font-weight: 700;
      line-height: 1;
    }

    .stat-value.wins   { color: #00ffb4; text-shadow: 0 0 16px #00ffb466; }
    .stat-value.losses { color: #e05a5a; text-shadow: 0 0 16px #e05a5a66; }
    .stat-value.ratio  { color: #c8d6e5; text-shadow: 0 0 16px #c8d6e533; }

    .panel {
      max-width: 700px;
      margin: 0 auto;
      background: #0d1117;
      border: 1px solid #00ffb422;
      border-radius: 8px;
      overflow: hidden;
    }

    .panel-header {
      padding: 0.75rem 1.25rem;
      border-bottom: 1px solid #00ffb422;
      font-family: 'Orbitron', sans-serif;
      font-size: 0.6rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: #00ffb4;
      opacity: 0.7;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #00ffb4;
      box-shadow: 0 0 6px #00ffb4;
      animation: blink 1.2s infinite;
      display: inline-block;
      margin-right: 6px;
    }

    @keyframes blink {
      0%,100% { opacity: 1; }
      50%      { opacity: 0.2; }
    }

    .event-row {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.65rem 1.25rem;
      border-bottom: 1px solid #00ffb411;
      font-size: 0.85rem;
      animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
      from { opacity: 0; transform: translateX(-10px); }
      to   { opacity: 1; transform: translateX(0); }
    }

    .event-row:last-child { border-bottom: none; }

    .badge {
      font-family: 'Orbitron', sans-serif;
      font-size: 0.55rem;
      letter-spacing: 0.1em;
      padding: 3px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      flex-shrink: 0;
    }

    .badge.win  { background: #00ffb411; color: #00ffb4; border: 1px solid #00ffb444; }
    .badge.loss { background: #e05a5a11; color: #e05a5a; border: 1px solid #e05a5a44; }

    .event-word { color: #c8d6e5; flex: 1; letter-spacing: 0.05em; }
    .event-time { color: #4a6080; font-size: 0.75rem; flex-shrink: 0; }

    .empty {
      padding: 2rem;
      text-align: center;
      color: #4a6080;
      font-size: 0.85rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>// Hangman Scoreboard</h1>
    <p>live game stats &mdash; auto-refreshes every 5s</p>
  </header>

  <div class="grid">
    <div class="stat-card">
      <div class="corner tl"></div><div class="corner tr"></div>
      <div class="corner bl"></div><div class="corner br"></div>
      <div class="stat-label">Wins</div>
      <div class="stat-value wins">{{ scores.wins }}</div>
    </div>
    <div class="stat-card">
      <div class="corner tl"></div><div class="corner tr"></div>
      <div class="corner bl"></div><div class="corner br"></div>
      <div class="stat-label">Losses</div>
      <div class="stat-value losses">{{ scores.losses }}</div>
    </div>
    <div class="stat-card">
      <div class="corner tl"></div><div class="corner tr"></div>
      <div class="corner bl"></div><div class="corner br"></div>
      <div class="stat-label">Win Rate</div>
      <div class="stat-value ratio">{{ win_rate }}%</div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <span><span class="live-dot"></span>Recent Events</span>
      <span>last {{ history|length }} games</span>
    </div>
    {% if history %}
      {% for event in history %}
      <div class="event-row">
        <span class="badge {{ event.result }}">{{ event.result }}</span>
        <span class="event-word">{{ event.word }}</span>
        <span class="event-time">{{ event.time }}</span>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">No games played yet. Start playing!</div>
    {% endif %}
  </div>

  <script>
    setTimeout(() => window.location.reload(), 5000);
  </script>
</body>
</html>"""


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SCOREBOARD_SECRET_KEY", secrets.token_hex(16))



    @app.route("/", methods=["GET"])
    def index() -> str:
        total = scores["wins"] + scores["losses"]
        win_rate = round(scores["wins"] / total * 100) if total > 0 else 0
        return render_template_string(
            TEMPLATE,
            scores=scores,
            history=list(reversed(history)),
            win_rate=win_rate,
        )

    @app.route("/event", methods=["POST"])
    def event() -> tuple:
        data = request.get_json(silent=True) or {}
        result = data.get("result", "").lower()
        word = data.get("word", "???")

        if result not in ("win", "loss"):
            return jsonify({"error": "result must be 'win' or 'loss'"}), 400

        if not isinstance(word, str) or len(word) > 30 or not word.isalpha():
            return jsonify({"status": "ignored"}), 200

        scores["wins" if result == "win" else "losses"] += 1
        history.append({
            "result": result,
            "word": word,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        return jsonify({"status": "ok", "scores": scores}), 200

    @app.route("/scores", methods=["GET"])
    def get_scores() -> tuple:
        return jsonify(scores), 200

    @app.route("/reset", methods=["POST"])
    def reset() -> tuple:
        scores["wins"] = 0
        scores["losses"] = 0
        history.clear()
        return jsonify({"status": "reset"}), 200

    return app


def main() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=False)


if __name__ == "__main__":
    main()
