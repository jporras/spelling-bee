from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from PyQt6.QtCore import QMarginsF
from PyQt6.QtGui import QPageLayout, QPageSize, QTextDocument, QPdfWriter


def build_user_report_html(snapshot: dict[str, object]) -> str:
    profile = snapshot.get("profile", {})
    level = escape(str(profile.get("difficulty_level", "B1")))
    user_id = escape(str(profile.get("user_id", "guest")))
    interactions = int(snapshot.get("interaction_count", 0))
    average_score = int(float(snapshot.get("average_score", 0.0)) * 100)
    top_mode = escape(str(snapshot.get("top_mode", "free")))
    notes = profile.get("notes", []) or []
    recent_errors = profile.get("recent_errors", []) or []
    last_session = snapshot.get("last_session") or {}
    spelling_history = snapshot.get("spelling_history", []) or []
    mode_usage = snapshot.get("mode_usage", {}) or {}

    notes_html = "".join(f"<li>{escape(str(note))}</li>" for note in notes[-5:]) or "<li>No notes yet.</li>"
    errors_html = "".join(f"<li>{escape(str(error))}</li>" for error in recent_errors[-6:]) or "<li>No recent errors.</li>"
    words_html = "".join(
        f"<li>{escape(str(item.get('word', '')))} - {'correct' if item.get('was_correct') else 'retry needed'}</li>"
        for item in spelling_history[:8]
        if item.get("word")
    ) or "<li>No spelling history yet.</li>"
    usage_html = "".join(
        f"<li>{escape(mode.title())}: {int(count)}</li>" for mode, count in mode_usage.items()
    ) or "<li>No usage recorded yet.</li>"
    resume_html = (
        f"""
        <p><strong>Last session mode:</strong> {escape(str(last_session.get('selected_mode', 'n/a')))}</p>
        <p><strong>Last session score:</strong> {int(float(last_session.get('evaluation_score', 0.0)) * 100)}%</p>
        <p><strong>Continue with:</strong> {escape(str(last_session.get('next_focus', 'keep practicing')))}</p>
        <p><strong>Summary:</strong> {escape(str(last_session.get('summary', '')))}</p>
        """
        if last_session
        else "<p>No previous session summary available.</p>"
    )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{ font-family: Segoe UI, Arial, sans-serif; color: #1f2933; margin: 24px; }}
          h1, h2 {{ color: #13212f; }}
          .card {{ border: 1px solid #d9cbb4; border-radius: 12px; padding: 14px; margin-bottom: 14px; }}
          .grid {{ width: 100%; border-collapse: collapse; }}
          .grid td {{ padding: 6px 10px; border-bottom: 1px solid #ece6d8; }}
          .muted {{ color: #5d6d7e; }}
        </style>
      </head>
      <body>
        <h1>Whisper Learning Report</h1>
        <p class="muted">Generated: {generated_at}</p>

        <div class="card">
          <h2>User Overview</h2>
          <table class="grid">
            <tr><td><strong>User</strong></td><td>{user_id}</td></tr>
            <tr><td><strong>Level</strong></td><td>{level}</td></tr>
            <tr><td><strong>Interactions</strong></td><td>{interactions}</td></tr>
            <tr><td><strong>Average score</strong></td><td>{average_score}%</td></tr>
            <tr><td><strong>Top mode</strong></td><td>{top_mode}</td></tr>
          </table>
        </div>

        <div class="card">
          <h2>Session Resume</h2>
          {resume_html}
        </div>

        <div class="card">
          <h2>Mode Usage</h2>
          <ul>{usage_html}</ul>
        </div>

        <div class="card">
          <h2>Recent Notes</h2>
          <ul>{notes_html}</ul>
        </div>

        <div class="card">
          <h2>Recent Errors</h2>
          <ul>{errors_html}</ul>
        </div>

        <div class="card">
          <h2>Spelling Memory</h2>
          <ul>{words_html}</ul>
        </div>
      </body>
    </html>
    """


def export_user_report_pdf(snapshot: dict[str, object], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(destination))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(18, 18, 18, 18),
        )
    )
    document = QTextDocument()
    document.setHtml(build_user_report_html(snapshot))
    document.print(writer)
    return destination
