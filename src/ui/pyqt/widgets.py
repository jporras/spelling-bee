from __future__ import annotations

import json
import re
from pathlib import Path

from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QTextEdit, QVBoxLayout, QWidget

from src.application.sub_agents import SubAgent
from src.domain.entities import AgentStep
from src.infrastructure.runtime_paths import get_resource_root
from src.ui.pyqt.themes import Theme


class CharacterAssetCatalog:
    def __init__(self, assets_root: Path) -> None:
        self._assets_root = assets_root

    def resolve(self, agent_id: str, state: str) -> Path | None:
        manifest_path = self._assets_root / agent_id / "manifest.json"
        if not manifest_path.exists():
            return None

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        states = data.get("states", {})
        relative_path = states.get(state) or states.get("idle")
        if not relative_path:
            return None

        candidate = self._assets_root / agent_id / relative_path
        return candidate if candidate.exists() else None


class DragHandle(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._color = QColor("#fefae0")

    def apply_theme(self, theme: Theme) -> None:
        self._color = QColor(theme.get("window_control_fg", "#fefae0"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color, 2)
        painter.setPen(pen)
        center_x = self.width() / 2
        center_y = self.height() / 2
        painter.drawLine(int(center_x), 4, int(center_x), self.height() - 4)
        painter.drawLine(4, int(center_y), self.width() - 4, int(center_y))
        painter.drawLine(int(center_x), 4, int(center_x - 3), 8)
        painter.drawLine(int(center_x), 4, int(center_x + 3), 8)
        painter.drawLine(int(center_x), self.height() - 4, int(center_x - 3), self.height() - 8)
        painter.drawLine(int(center_x), self.height() - 4, int(center_x + 3), self.height() - 8)
        painter.drawLine(4, int(center_y), 8, int(center_y - 3))
        painter.drawLine(4, int(center_y), 8, int(center_y + 3))
        painter.drawLine(self.width() - 4, int(center_y), self.width() - 8, int(center_y - 3))
        painter.drawLine(self.width() - 4, int(center_y), self.width() - 8, int(center_y + 3))


class GlyphToolButton(QToolButton):
    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._icon_color = QColor("#fefae0")
        self._surface_color = QColor("#13212f")
        self.setText("")

    def apply_theme(self, theme: Theme, *, use_window_palette: bool = False) -> None:
        surface = (
            theme.get("window_control_bg", "#13212f")
            if use_window_palette
            else theme.get("input_bg", "#fffdf8")
        )
        self.set_surface_color(surface)
        self.update()

    def set_surface_color(self, color: str) -> None:
        self._surface_color = QColor(color)
        self._icon_color = QColor("#fefae0" if _is_dark(self._surface_color) else "#13212f")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._icon_color)
        if not self.isEnabled():
            color.setAlpha(140)
        pen = QPen(color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = self.rect().adjusted(7, 7, -7, -7)

        if self._kind == "menu":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            dot_radius = max(2.0, min(rect.width(), rect.height()) / 9)
            center_x = rect.center().x()
            y_values = (
                rect.top() + dot_radius,
                rect.center().y(),
                rect.bottom() - dot_radius,
            )
            for y in y_values:
                painter.drawEllipse(QPointF(center_x, y), dot_radius, dot_radius)
        elif self._kind == "send":
            path = QPainterPath()
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right(), rect.center().y())
            path.lineTo(rect.left(), rect.bottom())
            path.lineTo(rect.left() + 4, rect.center().y())
            path.closeSubpath()
            painter.fillPath(path, color)
        elif self._kind == "listen":
            body_rect = QRectF(rect.left() + 4, rect.top() + 1, rect.width() - 8, rect.height() - 10)
            painter.drawRoundedRect(body_rect, 6, 6)
            painter.drawLine(int(rect.center().x()), int(body_rect.bottom()), int(rect.center().x()), rect.bottom() - 2)
            painter.drawLine(rect.left() + 4, rect.bottom() - 2, rect.right() - 4, rect.bottom() - 2)
        elif self._kind == "cancel":
            painter.drawLine(rect.left() + 2, rect.top() + 2, rect.right() - 2, rect.bottom() - 2)
            painter.drawLine(rect.right() - 2, rect.top() + 2, rect.left() + 2, rect.bottom() - 2)
        painter.end()


class PageNavButton(QToolButton):
    def __init__(self, direction: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._direction = direction
        self._color = QColor("#111111")
        self._background = QColor("#ffffff")
        self.setText("")
        self.setFixedSize(34, 22)

    def set_color(self, color: str) -> None:
        del color
        self._color = QColor("#111111")
        self._background = QColor("#ffffff")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._color)
        if not self.isEnabled():
            color.setAlpha(120)
        painter.setPen(Qt.PenStyle.NoPen)
        bg = QColor(self._background)
        bg.setAlpha(235 if self.isEnabled() else 180)
        painter.setBrush(bg)
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 9, 9)
        painter.setPen(QPen(QColor(0, 0, 0, 42), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 9, 9)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(
            self.width() / 2 - 5,
            self.height() / 2 - 5,
            10,
            10,
        )
        path = QPainterPath()
        if self._direction == "previous":
            path.moveTo(rect.right(), rect.top())
            path.lineTo(rect.left(), rect.center().y())
            path.lineTo(rect.right(), rect.bottom())
        else:
            path.moveTo(rect.left(), rect.top())
            path.lineTo(rect.right(), rect.center().y())
            path.lineTo(rect.left(), rect.bottom())
        path.closeSubpath()
        painter.drawPath(path)


def _is_dark(color: QColor) -> bool:
    return ((color.red() * 299) + (color.green() * 587) + (color.blue() * 114)) / 1000 < 140


class AudioLevelMeter(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level = 0.0
        self._active = False
        self._bar_color = QColor("#b42318")
        self._track_color = QColor("#e5dccd")
        self.setFixedHeight(18)
        self.setMinimumWidth(74)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        self.update()

    def apply_theme(self, theme: Theme) -> None:
        self._bar_color = QColor(theme.get("recording_button_bg", "#b42318"))
        self._track_color = QColor(theme.get("panel_border", "#e5dccd"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar_count = 8
        gap = 4
        available_width = self.width() - (gap * (bar_count - 1))
        bar_width = max(4, int(available_width / bar_count))
        active_bars = max(1, int(round(self._level * bar_count))) if self._active else 0
        for index in range(bar_count):
            x = index * (bar_width + gap)
            height_factor = 0.35 + (index % 3) * 0.18
            bar_height = int(self.height() * min(0.95, height_factor + 0.2))
            y = self.height() - bar_height
            color = QColor(self._bar_color if index < active_bars else self._track_color)
            if not self._active:
                color.setAlpha(120)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_height), 3, 3)


class CharacterPortrait(QWidget):
    STATE_COLORS = {
        "idle": ("#24415f", "#8fb9d9"),
        "active": ("#572d4d", "#ffb347"),
        "completed": ("#204a44", "#7bd8c6"),
    }

    def __init__(
        self,
        sub_agent: SubAgent,
        assets: CharacterAssetCatalog,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sub_agent = sub_agent
        self._assets = assets
        self._state = "idle"
        self._compact = True
        self._pixmap: QPixmap | None = None
        self.set_density(True)
        self._load_state_art()

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        self.setMinimumSize(276, 414) if compact else self.setMinimumSize(492, 696)

    def set_state(self, state: str) -> None:
        self._state = state
        self._load_state_art()
        self.update()

    def _load_state_art(self) -> None:
        path = self._assets.resolve(self.sub_agent.agent_id, self._state)
        self._pixmap = QPixmap(str(path)) if path else None
        if self._pixmap is not None and self._pixmap.isNull():
            self._pixmap = None

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._pixmap is not None:
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) / 2
            y = self.height() - scaled.height()
            painter.drawPixmap(int(x), int(y), scaled)
            return

        bg = QPainterPath()
        bg.addRoundedRect(QRectF(self.rect()), 28, 28)
        painter.fillPath(bg, QColor("#f9f4ea"))

        primary, accent = self.STATE_COLORS.get(self._state, self.STATE_COLORS["idle"])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(primary))
        painter.drawEllipse(QRectF(112, 44, 116, 116))

        body = QPainterPath()
        body.moveTo(170, 150)
        body.cubicTo(300, 170, 330, 335, 282, 430)
        body.lineTo(58, 430)
        body.cubicTo(20, 340, 52, 170, 170, 150)
        painter.setBrush(QColor(accent))
        painter.drawPath(body)

        painter.setBrush(QColor(primary))
        painter.drawRoundedRect(QRectF(82, 224, 176, 172), 28, 28)

        painter.setPen(QPen(QColor("#13212f"), 4))
        painter.drawArc(145, 96, 52, 34, 0, -180 * 16)
        painter.drawPoint(QPointF(148, 100))
        painter.drawPoint(QPointF(194, 100))

        painter.setPen(QColor("#13212f"))
        font = QFont("Segoe UI", 17, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            QRectF(40, 350, self.width() - 80, 48),
            Qt.AlignmentFlag.AlignCenter,
            self.sub_agent.display_name,
        )


class DialogueBubble(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = "idle"
        self._compact = True
        self._speaker_color = "#13212f"
        self._status_color = "#5d6d7e"
        self._text_color = "#1f2933"
        self._hint_color = "#5d6d7e"
        self._full_text = "The active ukagaka will speak here."
        self._pages: list[str] = []
        self._page_index = 0
        resource_root = get_resource_root(Path(__file__).resolve().parents[3])
        self._svg_template = (resource_root / "assets" / "ui" / "balloons" / "speech_right.svg").read_text(encoding="utf-8")
        self._renderer = QSvgRenderer()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("dialogueBubble")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self)
        self._layout = layout

        self.content_box = QWidget(self)
        self.content_box.setObjectName("dialogueContent")
        self.content_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(self.content_box)
        self._content_layout = content_layout

        self.speaker_label = QLabel("Orion", self.content_box)
        self.speaker_label.setObjectName("speakerLabel")
        self.status_label = QLabel("Ready", self.content_box)
        self.status_label.setObjectName("statusLabel")
        self.text_label = QLabel("The active ukagaka will speak here.", self.content_box)
        self.text_label.setWordWrap(True)
        self.text_label.setObjectName("textLabel")
        self.page_hint_label = QLabel("", self.content_box)
        self.page_hint_label.setObjectName("pageHintLabel")
        self.page_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_nav_row = QWidget(self)
        self.page_nav_row.setObjectName("pageNavRow")
        self.prev_page_button = PageNavButton("previous", self.page_nav_row)
        self.prev_page_button.setObjectName("pageNavButton")
        self.prev_page_button.clicked.connect(self._show_previous_page)
        self.next_page_button = PageNavButton("next", self.page_nav_row)
        self.next_page_button.setObjectName("pageNavButton")
        self.next_page_button.clicked.connect(self._show_next_page)
        nav_layout = QHBoxLayout(self.page_nav_row)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)
        nav_layout.addWidget(self.prev_page_button)
        nav_layout.addWidget(self.page_hint_label, stretch=1)
        nav_layout.addWidget(self.next_page_button)

        content_layout.addWidget(self.speaker_label)
        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.text_label)
        content_layout.addStretch(1)
        layout.addSpacing(30)
        layout.addWidget(self.content_box, stretch=1)
        layout.addStretch(1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)
        self.set_density(True)
        self._apply_style()

    def set_message(self, speaker: str, status: str, text: str, state: str) -> None:
        self._state = state
        self._full_text = text
        self.speaker_label.setText(speaker)
        self.status_label.setText(status)
        self._pages = _paginate_dialogue(self._full_text, compact=self._compact)
        self._page_index = 0
        self._render_current_page()
        self._apply_style()

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        if compact:
            self._layout.setContentsMargins(68, 44, 120, 88)
            self.content_box.setMinimumWidth(0)
            self.content_box.setMaximumWidth(16777215)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(6)
        else:
            self._layout.setContentsMargins(82, 58, 138, 108)
            self.content_box.setMinimumWidth(0)
            self.content_box.setMaximumWidth(16777215)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(8)
        if self._full_text:
            self._pages = _paginate_dialogue(self._full_text, compact=self._compact)
            self._page_index = 0
            self._render_current_page()
        self._apply_style()

    def _apply_style(self) -> None:
        self._speaker_color = "#13212f"
        self._status_color = "#5d6d7e"
        self._text_color = "#1f2933"
        self._hint_color = "#5d6d7e"
        self._load_renderer("#ffffff", "#222222")
        speaker_size = 18 if self._compact else 21
        status_size = 12 if self._compact else 14
        text_size = 14 if self._compact else 17
        hint_size = 10 if self._compact else 11
        self.prev_page_button.set_color(self._speaker_color)
        self.next_page_button.set_color(self._speaker_color)
        self.setStyleSheet(
            f"""
            QFrame#dialogueBubble {{
                background: transparent;
                border: none;
            }}
            QWidget#dialogueContent {{
                background: transparent;
            }}
            QLabel#speakerLabel {{
                color: {self._speaker_color};
                font-size: {speaker_size}px;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#statusLabel {{
                color: {self._status_color};
                font-size: {status_size}px;
                background: transparent;
            }}
            QLabel#textLabel {{
                color: {self._text_color};
                font-size: {text_size}px;
                background: transparent;
            }}
            QLabel#pageHintLabel {{
                color: {self._hint_color};
                font-size: {hint_size}px;
                background: transparent;
                padding-top: 2px;
            }}
            QWidget#pageNavRow {{
                background: transparent;
            }}
            QToolButton#pageNavButton {{
                min-width: 34px;
                min-height: 22px;
                max-width: 34px;
                max-height: 22px;
                border: none;
                background: transparent;
                padding: 0;
            }}
            """
        )
        self.update()

    def apply_theme(self, theme: Theme) -> None:
        self._speaker_color = theme.get('dialogue_speaker', '#13212f')
        self._status_color = theme.get('dialogue_status', '#5d6d7e')
        self._text_color = theme.get('dialogue_text', '#1f2933')
        self._hint_color = theme.get('dialogue_status', '#5d6d7e')
        self._load_renderer(
            theme.get("dialogue_bg", "#ffffff"),
            theme.get("dialogue_border", theme.get("window_control_bg", "#222222")),
        )
        speaker_size = 18 if self._compact else 21
        status_size = 12 if self._compact else 14
        text_size = 14 if self._compact else 17
        hint_size = 10 if self._compact else 11
        self.prev_page_button.set_color(self._speaker_color)
        self.next_page_button.set_color(self._speaker_color)
        self.setStyleSheet(
            f"""
            QFrame#dialogueBubble {{
                background: transparent;
                border: none;
            }}
            QWidget#dialogueContent {{
                background: transparent;
            }}
            QLabel#speakerLabel {{
                color: {self._speaker_color};
                font-size: {speaker_size}px;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#statusLabel {{
                color: {self._status_color};
                font-size: {status_size}px;
                background: transparent;
            }}
            QLabel#textLabel {{
                color: {self._text_color};
                font-size: {text_size}px;
                background: transparent;
            }}
            QLabel#pageHintLabel {{
                color: {self._hint_color};
                font-size: {hint_size}px;
                background: transparent;
                padding-top: 2px;
            }}
            QWidget#pageNavRow {{
                background: transparent;
            }}
            QToolButton#pageNavButton {{
                min-width: 34px;
                min-height: 22px;
                max-width: 34px;
                max-height: 22px;
                border: none;
                background: transparent;
                padding: 0;
            }}
            """
        )
        self.update()

    def _render_current_page(self) -> None:
        page_text = self._pages[self._page_index] if self._pages else ""
        self.text_label.setText(_to_dialogue_html(page_text))
        if len(self._pages) > 1:
            self.page_nav_row.setVisible(True)
            self._position_page_navigation()
            self.page_hint_label.setText(f"{self._page_index + 1}/{len(self._pages)}")
            self.prev_page_button.setEnabled(self._page_index > 0)
            self.next_page_button.setEnabled(self._page_index < len(self._pages) - 1)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.page_nav_row.setVisible(False)
            self.page_hint_label.setText("")
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_page_navigation()

    def _position_page_navigation(self) -> None:
        if not hasattr(self, "page_nav_row"):
            return
        nav_width = min(220, max(160, self.width() - 160))
        nav_height = 24
        bottom_clearance = 44 if self._compact else 58
        x = int((self.width() - nav_width) / 2)
        y = max(0, self.height() - bottom_clearance - nav_height)
        self.page_nav_row.setGeometry(x, y, nav_width, nav_height)
        self.page_nav_row.raise_()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and len(self._pages) > 1:
            if self._page_index < len(self._pages) - 1:
                self._show_next_page()
                event.accept()
                return
        super().mousePressEvent(event)

    def _show_previous_page(self) -> None:
        if self._page_index <= 0:
            return
        self._page_index -= 1
        self._render_current_page()

    def _show_next_page(self) -> None:
        if self._page_index >= len(self._pages) - 1:
            return
        self._page_index += 1
        self._render_current_page()

    def _load_renderer(self, fill: str, stroke: str) -> None:
        svg = self._svg_template.replace("{{FILL}}", fill).replace("{{STROKE}}", stroke)
        self._renderer.load(QByteArray(svg.encode("utf-8")))

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._renderer.isValid():
            self._renderer.render(painter, QRectF(self.rect()))


def _paginate_dialogue(text: str, *, compact: bool) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return [""]

    paragraph_limit = 6 if compact else 7
    char_limit = 520 if compact else 760
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]
    if not paragraphs:
        paragraphs = [normalized]

    pages: list[str] = []
    current: list[str] = []
    current_chars = 0
    for paragraph in paragraphs:
        if current and (len(current) >= paragraph_limit or current_chars + len(paragraph) > char_limit):
            pages.append("\n\n".join(current))
            current = []
            current_chars = 0
        current.append(paragraph)
        current_chars += len(paragraph)

    if current:
        pages.append("\n\n".join(current))
    return pages or [normalized]


def _to_dialogue_html(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    return "".join(
        f"<p style='margin:0 0 6px 0; line-height:1.25;'>{_escape_html(paragraph)}</p>"
        for paragraph in paragraphs
        if paragraph
    )


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class AgentRoster(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: dict[str, QLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("agentRoster")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        self._layout = layout
        self.setStyleSheet(
            """
            QFrame#agentRoster {
                background: rgba(255,255,255,0.7);
                border: 2px solid #d9cbb4;
                border-radius: 18px;
            }
            QLabel {
                color: #1f2933;
                font-size: 13px;
                padding: 8px 10px;
                border-radius: 12px;
                background: rgba(36, 65, 95, 0.08);
            }
            """
        )

    def register_agents(self, agents: list[SubAgent]) -> None:
        for agent in agents:
            label = QLabel(f"{agent.display_name} Â· idle", self)
            self._items[agent.agent_id] = label
            self._layout.addWidget(label)

    def mark_idle(self) -> None:
        for label in self._items.values():
            label.setStyleSheet("")

    def set_state(self, agent_id: str, state: str, summary: str) -> None:
        label = self._items.get(agent_id)
        if label is None:
            return
        color = {
            "idle": "#8da6bf",
            "active": "#ffb347",
            "completed": "#7bd8c6",
        }.get(state, "#8da6bf")
        display_summary = summary if len(summary) <= 42 else f"{summary[:39]}..."
        label.setText(f"{agent_id} Â· {display_summary}")
        label.setStyleSheet(
            f"background: {color}; color: #13212f; font-weight: 600; padding: 8px 10px; border-radius: 12px;"
        )


class ConversationPanel(QTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("conversationPanel")
        self._compact = True
        self.set_density(True)
        self.setStyleSheet(
            """
            QTextEdit#conversationPanel {
                background: #fffdf8;
                border: 2px solid #d9cbb4;
                border-radius: 16px;
                color: #1f2933;
                padding: 10px;
            }
            """
        )

    def append_message(self, speaker: str, text: str) -> None:
        self.append(f"<b>{speaker}:</b> {text}")

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        self.setMinimumHeight(120 if compact else 180)

    def apply_theme(self, theme: Theme) -> None:
        self.setStyleSheet(
            f"""
            QTextEdit#conversationPanel {{
                background: {theme.get('conversation_bg', '#fffdf8')};
                border: 2px solid {theme.get('panel_border', '#d9cbb4')};
                border-radius: 16px;
                color: {theme.get('conversation_text', '#1f2933')};
                padding: 10px;
            }}
            """
        )


class MetricBar(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self._value = 0.0
        self._compact = True
        self._text_color = QColor("#213547")
        self._track_color = QColor("#e7ecef")
        self._fill_color = QColor("#355070")
        self.setMinimumHeight(42)

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        self.setMinimumHeight(38 if compact else 48)
        self.update()

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self.update()

    def apply_theme(self, theme: Theme) -> None:
        self._text_color = QColor(theme.get("panel_text", "#213547"))
        self._track_color = QColor(theme.get("chart_track", "#e7ecef"))
        self._fill_color = QColor(theme.get("chart_fill", "#355070"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label_font = QFont("Segoe UI", 9 if self._compact else 10, QFont.Weight.DemiBold)
        value_font = QFont("Segoe UI", 8 if self._compact else 9)
        painter.setPen(self._text_color)
        painter.setFont(label_font)
        painter.drawText(0, 12 if self._compact else 14, self._label)
        painter.setFont(value_font)
        painter.drawText(self.width() - 42, 12 if self._compact else 14, f"{int(self._value * 100)}%")

        bar_top = 18 if self._compact else 22
        bar_height = 12 if self._compact else 14
        track_rect = QRectF(0, bar_top, self.width(), bar_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._track_color)
        painter.drawRoundedRect(track_rect, bar_height / 2, bar_height / 2)
        fill_rect = QRectF(0, bar_top, self.width() * self._value, bar_height)
        painter.setBrush(self._fill_color)
        painter.drawRoundedRect(fill_rect, bar_height / 2, bar_height / 2)


class TrendChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self._compact = True
        self._line_color = QColor("#355070")
        self._fill_color = QColor(53, 80, 112, 48)
        self._grid_color = QColor("#d9cbb4")
        self._text_color = QColor("#213547")
        self.setMinimumHeight(110)

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        self.setMinimumHeight(96 if compact else 126)
        self.update()

    def set_values(self, values: list[float]) -> None:
        self._values = values[-10:]
        self.update()

    def apply_theme(self, theme: Theme) -> None:
        self._line_color = QColor(theme.get("chart_fill", "#355070"))
        self._fill_color = QColor(theme.get("chart_fill_soft", "rgba(53, 80, 112, 0.2)"))
        self._grid_color = QColor(theme.get("panel_border", "#d9cbb4"))
        self._text_color = QColor(theme.get("panel_text", "#213547"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -20)
        painter.setPen(QPen(self._grid_color, 1))
        for fraction in (0.25, 0.5, 0.75):
            y = rect.top() + rect.height() * fraction
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
        painter.setPen(self._text_color)
        painter.setFont(QFont("Segoe UI", 8 if self._compact else 9))
        painter.drawText(rect.left(), self.height() - 4, "Progress")
        if len(self._values) < 2:
            return

        max_value = 1.0
        min_value = 0.0
        x_step = rect.width() / max(1, len(self._values) - 1)
        points = []
        for index, value in enumerate(self._values):
            x = rect.left() + x_step * index
            normalized = (value - min_value) / (max_value - min_value or 1.0)
            y = rect.bottom() - normalized * rect.height()
            points.append(QPointF(x, y))

        fill_path = QPainterPath()
        fill_path.moveTo(points[0])
        for point in points[1:]:
            fill_path.lineTo(point)
        fill_path.lineTo(points[-1].x(), rect.bottom())
        fill_path.lineTo(points[0].x(), rect.bottom())
        fill_path.closeSubpath()
        painter.fillPath(fill_path, self._fill_color)

        painter.setPen(QPen(self._line_color, 2.5))
        for first, second in zip(points, points[1:]):
            painter.drawLine(int(first.x()), int(first.y()), int(second.x()), int(second.y()))
        painter.setBrush(self._line_color)
        painter.setPen(Qt.PenStyle.NoPen)
        for point in points:
            painter.drawEllipse(point, 3, 3)


class UserDashboard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._compact = True
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("userDashboard")
        layout = QVBoxLayout(self)
        self._layout = layout

        self.user_label = QLabel("User: guest", self)
        self.level_label = QLabel("Level: B1", self)
        self.score_label = QLabel("Average score: 0%", self)
        self.focus_label = QLabel("Next focus: start practicing", self)
        self.session_label = QLabel("Resume from: no previous session", self)
        self.spell_memory_label = QLabel("Spell memory: none", self)
        self.errors_label = QLabel("Recent errors: none", self)

        self.metrics_grid = QGridLayout()
        self.metrics_grid.setContentsMargins(0, 0, 0, 0)
        self.metrics_grid.setHorizontalSpacing(10)
        self.metrics_grid.setVerticalSpacing(8)

        self.level_progress = MetricBar("Level Progress", self)
        self.grammar_bar = MetricBar("Grammar", self)
        self.talk_bar = MetricBar("Talk", self)
        self.listen_bar = MetricBar("Listen", self)
        self.spell_bar = MetricBar("Spell", self)
        self.trend_chart = TrendChart(self)

        self.metrics_grid.addWidget(self.level_progress, 0, 0)
        self.metrics_grid.addWidget(self.grammar_bar, 0, 1)
        self.metrics_grid.addWidget(self.talk_bar, 1, 0)
        self.metrics_grid.addWidget(self.listen_bar, 1, 1)
        self.metrics_grid.addWidget(self.spell_bar, 2, 0, 1, 2)

        for label in (
            self.user_label,
            self.level_label,
            self.score_label,
            self.focus_label,
            self.session_label,
            self.spell_memory_label,
            self.errors_label,
        ):
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addLayout(self.metrics_grid)
        layout.addWidget(self.trend_chart)

        self.setStyleSheet(
            """
            QFrame#userDashboard {
                background: #fffdf8;
                border: 2px solid #d9cbb4;
                border-radius: 18px;
            }
            QLabel {
                color: #213547;
                font-size: 12px;
            }
            """
        )
        self.set_density(True)

    def set_density(self, compact: bool) -> None:
        self._compact = compact
        self._layout.setContentsMargins(12, 12, 12, 12) if compact else self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(6 if compact else 10)
        font_size = 12 if compact else 14
        self.level_progress.set_density(compact)
        self.grammar_bar.set_density(compact)
        self.talk_bar.set_density(compact)
        self.listen_bar.set_density(compact)
        self.spell_bar.set_density(compact)
        self.trend_chart.set_density(compact)
        self.setStyleSheet(
            f"""
            QFrame#userDashboard {{
                background: #fffdf8;
                border: 2px solid #d9cbb4;
                border-radius: 18px;
            }}
            QLabel {{
                color: #213547;
                font-size: {font_size}px;
            }}
            """
        )

    def update_snapshot(
        self,
        snapshot: dict[str, object],
        metadata: dict[str, object] | None = None,
    ) -> None:
        profile = snapshot.get("profile", {})
        self.user_label.setText(f"User: {profile.get('user_id', 'guest')}")
        self.level_label.setText(f"Level: {profile.get('difficulty_level', 'B1')}")
        errors = profile.get("recent_errors", []) or ["none"]
        self.errors_label.setText(f"Recent errors: {', '.join(errors)}")
        last_session = snapshot.get("last_session")
        if last_session:
            self.session_label.setText(
                "Resume from: "
                f"{last_session.get('selected_mode', 'free')} | "
                f"level {last_session.get('level', 'B1')} | "
                f"{int(float(last_session.get('evaluation_score', 0.0)) * 100)}%"
            )
        else:
            self.session_label.setText("Resume from: no previous session")
        spelling_history = snapshot.get("spelling_history", [])
        if spelling_history:
            recent_words = ", ".join(item["word"] for item in spelling_history[:5])
            self.spell_memory_label.setText(f"Spell memory: {recent_words}")
        else:
            self.spell_memory_label.setText("Spell memory: none")
        mode_usage = snapshot.get("mode_usage", {})
        total_interactions = max(1, int(snapshot.get("interaction_count", 0)))
        self.level_progress.set_value(float(snapshot.get("level_index", 1)) / max(1, float(snapshot.get("level_scale", 4))))
        self.grammar_bar.set_value(float(mode_usage.get("grammar", 0)) / total_interactions)
        self.talk_bar.set_value(float(mode_usage.get("talk", 0)) / total_interactions)
        self.listen_bar.set_value(float(mode_usage.get("listen", 0)) / total_interactions)
        self.spell_bar.set_value(float(mode_usage.get("spell", 0)) / total_interactions)
        self.trend_chart.set_values([float(value) for value in snapshot.get("recent_scores", [])])
        if metadata:
            self.score_label.setText(
                f"Average score: {int(float(snapshot.get('average_score', 0.0)) * 100)}% | Last: {int(float(metadata.get('evaluation_score', 0.0)) * 100)}%"
            )
            self.focus_label.setText(f"Next focus: {metadata.get('next_focus', 'keep practicing')}")
        else:
            self.score_label.setText(f"Average score: {int(float(snapshot.get('average_score', 0.0)) * 100)}%")
            notes = profile.get("notes", [])
            self.focus_label.setText(
                f"Next focus: {notes[-1] if notes else 'start practicing'}"
            )

    def apply_theme(self, theme: Theme) -> None:
        font_size = 12 if self._compact else 14
        self.level_progress.apply_theme(theme)
        self.grammar_bar.apply_theme(theme)
        self.talk_bar.apply_theme(theme)
        self.listen_bar.apply_theme(theme)
        self.spell_bar.apply_theme(theme)
        self.trend_chart.apply_theme(theme)
        self.setStyleSheet(
            f"""
            QFrame#userDashboard {{
                background: {theme.get('panel_bg', '#fffdf8')};
                border: 2px solid {theme.get('panel_border', '#d9cbb4')};
                border-radius: 18px;
            }}
            QLabel {{
                color: {theme.get('panel_text', '#213547')};
                font-size: {font_size}px;
            }}
            """
        )
