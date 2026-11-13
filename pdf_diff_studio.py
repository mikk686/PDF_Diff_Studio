import difflib
from pathlib import Path
import sys
import cv2
import fitz  # PyMuPDF
import numpy as np
from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# ================= MODERN DARK STYLESHEET =================
MODERN_QSS = """
QMainWindow, QWidget#Root {
    background-color: #0D1117;
    color: #E6EDF3;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
}
QFrame#TopBar, QFrame#BottomBar {
    background-color: #161B22;
    border-bottom: 1px solid #262C36;
}
QFrame#BottomBar {
    border-top: 1px solid #262C36;
    border-bottom: none;
}
QFrame#PaneCard {
    background-color: #12161E;
    border: 1px solid #262C36;
    border-radius: 10px;
}
QFrame#PaneHeader {
    background-color: #161B22;
    border-bottom: 1px solid #262C36;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
}
QPushButton {
    background-color: #21262D;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363D;
    border-color: #484F58;
}
QPushButton:pressed {
    background-color: #161B22;
}
QPushButton:disabled {
    color: #484F58;
    background-color: #161B22;
    border-color: #21262D;
}
QPushButton#AccentBtn {
    background-color: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
    font-weight: 600;
}
QPushButton#AccentBtn:hover {
    background-color: #1D4ED8;
}
QPushButton#ModeBtn {
    border-radius: 6px;
    padding: 6px 14px;
    background-color: transparent;
    border: 1px solid transparent;
    color: #8B949E;
}
QPushButton#ModeBtn:hover {
    color: #E6EDF3;
    background-color: #21262D;
}
QPushButton#ModeBtn:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #0D1117;
    width: 10px;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #30363D;
    border-radius: 5px;
    min-height: 24px;
    min-width: 24px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #484F58;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}
QCheckBox {
    color: #C9D1D9;
    font-size: 13px;
    spacing: 6px;
}
"""


class DropScrollArea(QScrollArea):
  """Scroll area supporting PDF Drag & Drop."""

  file_dropped = pyqtSignal(str)

  def __init__(self, placeholder_text: str):
    super().__init__()
    self.setWidgetResizable(True)
    self.setAcceptDrops(True)
    self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    self.content_label = QLabel(placeholder_text)
    self.content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.content_label.setStyleSheet(
        "color: #6E7681; font-size: 15px; padding: 40px; border: 2px dashed"
        " #262C36; border-radius: 12px; margin: 24px;"
    )
    self.setWidget(self.content_label)
    self.has_image = False

  def set_pixmap(self, pixmap: QPixmap):
    self.has_image = True
    self.content_label.setStyleSheet("padding: 16px; border: none; margin: 0;")
    self.content_label.setPixmap(pixmap)

  def set_message(self, message: str):
    self.has_image = False
    self.content_label.clear()
    self.content_label.setStyleSheet(
        "color: #6E7681; font-size: 15px; padding: 40px; border: 2px dashed"
        " #262C36; border-radius: 12px; margin: 24px;"
    )
    self.content_label.setText(message)

  def dragEnterEvent(self, event: QDragEnterEvent):
    if event.mimeData().hasUrls():
      urls = event.mimeData().urls()
      if urls and urls[0].toLocalFile().lower().endswith(".pdf"):
        event.acceptProposedAction()

  def dropEvent(self, event: QDropEvent):
    urls = event.mimeData().urls()
    if urls:
      file_path = urls[0].toLocalFile()
      if file_path.lower().endswith(".pdf"):
        self.file_dropped.emit(file_path)


class PDFPane(QFrame):
  """Single Left or Right PDF Viewer Panel."""

  pdf_loaded = pyqtSignal(str)

  def __init__(self, title: str, placeholder: str):
    super().__init__()
    self.setObjectName("PaneCard")
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # Header
    header = QFrame()
    header.setObjectName("PaneHeader")
    h_layout = QHBoxLayout(header)
    h_layout.setContentsMargins(14, 10, 14, 10)

    self.title_lbl = QLabel(title)
    self.title_lbl.setStyleSheet(
        "font-weight: 600; font-size: 13px; color: #8B949E;"
    )

    self.file_lbl = QLabel("No file selected")
    self.file_lbl.setStyleSheet(
        "font-weight: 600; font-size: 13px; color: #E6EDF3;"
    )

    self.open_btn = QPushButton("Load PDF...")
    self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    self.open_btn.clicked.connect(self.browse_file)

    h_layout.addWidget(self.title_lbl)
    h_layout.addWidget(QLabel("·"))
    h_layout.addWidget(self.file_lbl, 1)
    h_layout.addWidget(self.open_btn)

    # Viewer Area
    self.scroll_area = DropScrollArea(placeholder)
    self.scroll_area.file_dropped.connect(self._on_file_selected)

    layout.addWidget(header)
    layout.addWidget(self.scroll_area, 1)

  def browse_file(self):
    path, _ = QFileDialog.getOpenFileName(
        self, "Select PDF File", "", "PDF Files (*.pdf)"
    )
    if path:
      self._on_file_selected(path)

  def _on_file_selected(self, path: str):
    self.file_lbl.setText(Path(path).name)
    self.file_lbl.setToolTip(path)
    self.pdf_loaded.emit(path)


class PDFDiffStudio(QMainWindow):

  def __init__(self):
    super().__init__()
    self.setWindowTitle("PDF Diff Studio")
    self.resize(1440, 900)

    self.doc1: fitz.Document | None = None
    self.doc2: fitz.Document | None = None
    self.current_page = 0
    self.zoom = 1.4  # Default crisp scale
    self.mode = "text"  # 'text', 'pixel', 'both'
    self._syncing_scroll = False

    self._build_ui()

  def _build_ui(self):
    root = QWidget()
    root.setObjectName("Root")
    self.setCentralWidget(root)
    main_layout = QVBoxLayout(root)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # ================= TOP TOOLBAR =================
    top_bar = QFrame()
    top_bar.setObjectName("TopBar")
    top_layout = QHBoxLayout(top_bar)
    top_layout.setContentsMargins(20, 12, 20, 12)
    top_layout.setSpacing(12)

    brand = QLabel("PDF Diff Studio")
    brand.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
    brand.setStyleSheet("color: #FFFFFF; letter-spacing: 0.3px;")
    top_layout.addWidget(brand)
    top_layout.addSpacing(20)

    # Mode Switcher Container
    mode_frame = QFrame()
    mode_frame.setStyleSheet(
        "background-color: #0D1117; border: 1px solid #262C36; border-radius:"
        " 8px; padding: 2px;"
    )
    mode_layout = QHBoxLayout(mode_frame)
    mode_layout.setContentsMargins(2, 2, 2, 2)
    mode_layout.setSpacing(4)

    self.mode_group = QButtonGroup(self)
    modes = [
        ("Text Diff", "text"),
        ("Pixel Diff", "pixel"),
        ("Combined", "both"),
    ]
    for idx, (label, val) in enumerate(modes):
      btn = QPushButton(label)
      btn.setObjectName("ModeBtn")
      btn.setCheckable(True)
      btn.setCursor(Qt.CursorShape.PointingHandCursor)
      if val == "text":
        btn.setChecked(True)
      btn.clicked.connect(lambda checked, v=val: self.set_mode(v))
      self.mode_group.addButton(btn, idx)
      mode_layout.addWidget(btn)

    top_layout.addWidget(mode_frame)
    top_layout.addStretch(1)

    # Sync Scroll Checkbox
    self.sync_cb = QCheckBox("Sync Scroll")
    self.sync_cb.setChecked(True)
    top_layout.addWidget(self.sync_cb)
    top_layout.addSpacing(12)

    # Zoom Controls
    zoom_out_btn = QPushButton("−")
    zoom_out_btn.setFixedWidth(34)
    zoom_out_btn.clicked.connect(lambda: self.change_zoom(-0.2))

    self.zoom_lbl = QLabel("100%")
    self.zoom_lbl.setFixedWidth(48)
    self.zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.zoom_lbl.setStyleSheet("color: #8B949E; font-weight: 600;")

    zoom_in_btn = QPushButton("+")
    zoom_in_btn.setFixedWidth(34)
    zoom_in_btn.clicked.connect(lambda: self.change_zoom(0.2))

    top_layout.addWidget(zoom_out_btn)
    top_layout.addWidget(self.zoom_lbl)
    top_layout.addWidget(zoom_in_btn)

    # ================= SPLIT VIEWER WORKSPACE =================
    workspace = QHBoxLayout()
    workspace.setContentsMargins(16, 16, 16, 16)
    workspace.setSpacing(16)

    self.left_pane = PDFPane(
        "ORIGINAL",
        "Drop Original PDF here\nor click 'Load PDF...'",
    )
    self.right_pane = PDFPane(
        "MODIFIED",
        "Drop Modified PDF here\nor click 'Load PDF...'",
    )

    self.left_pane.pdf_loaded.connect(self.load_left_pdf)
    self.right_pane.pdf_loaded.connect(self.load_right_pdf)

    # Connect Synchronized Scrolling
    self._connect_scrollbars(
        self.left_pane.scroll_area.verticalScrollBar(),
        self.right_pane.scroll_area.verticalScrollBar(),
    )
    self._connect_scrollbars(
        self.left_pane.scroll_area.horizontalScrollBar(),
        self.right_pane.scroll_area.horizontalScrollBar(),
    )

    workspace.addWidget(self.left_pane, 1)
    workspace.addWidget(self.right_pane, 1)

    # ================= BOTTOM NAVIGATION & LEGEND =================
    bottom_bar = QFrame()
    bottom_bar.setObjectName("BottomBar")
    bot_layout = QHBoxLayout(bottom_bar)
    bot_layout.setContentsMargins(20, 10, 20, 10)

    # Legend
    legend = QLabel(
        "<span style='color:#F85149;'>■</span> Removed / Changed   "
        "&nbsp;&nbsp;<span style='color:#2EA043;'>■</span> Added / Changed   "
        "&nbsp;&nbsp;<span style='color:#A855F7;'>■</span> Pixel Difference"
    )
    legend.setStyleSheet("font-size: 12px; color: #8B949E;")
    bot_layout.addWidget(legend)
    bot_layout.addStretch(1)

    # Page Controls
    self.prev_btn = QPushButton("◀ Prev")
    self.prev_btn.setEnabled(False)
    self.prev_btn.clicked.connect(lambda: self.go_to_page(self.current_page - 1))

    self.page_lbl = QLabel("Page 0 / 0")
    self.page_lbl.setMinimumWidth(100)
    self.page_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.page_lbl.setStyleSheet("font-weight: 600; color: #E6EDF3;")

    self.next_btn = QPushButton("Next ▶")
    self.next_btn.setEnabled(False)
    self.next_btn.clicked.connect(lambda: self.go_to_page(self.current_page + 1))

    self.next_diff_btn = QPushButton("Next Diff ⚡")
    self.next_diff_btn.setObjectName("AccentBtn")
    self.next_diff_btn.setEnabled(False)
    self.next_diff_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    self.next_diff_btn.clicked.connect(self.jump_to_next_diff)

    bot_layout.addWidget(self.prev_btn)
    bot_layout.addWidget(self.page_lbl)
    bot_layout.addWidget(self.next_btn)
    bot_layout.addSpacing(12)
    bot_layout.addWidget(self.next_diff_btn)

    bot_layout.addStretch(1)

    self.stats_lbl = QLabel("Load two PDFs to start comparison")
    self.stats_lbl.setStyleSheet(
        "font-size: 13px; color: #8B949E; font-weight: 500;"
    )
    bot_layout.addWidget(self.stats_lbl)

    main_layout.addWidget(top_bar)
    main_layout.addLayout(workspace, 1)
    main_layout.addWidget(bottom_bar)

  def _connect_scrollbars(self, bar1, bar2):
    def sync_1_to_2(val):
      if self.sync_cb.isChecked() and not self._syncing_scroll:
        self._syncing_scroll = True
        bar2.setValue(val)
        self._syncing_scroll = False

    def sync_2_to_1(val):
      if self.sync_cb.isChecked() and not self._syncing_scroll:
        self._syncing_scroll = True
        bar1.setValue(val)
        self._syncing_scroll = False

    bar1.valueChanged.connect(sync_1_to_2)
    bar2.valueChanged.connect(sync_2_to_1)

  # ================= STATE & NAVIGATION =================
  def load_left_pdf(self, path: str):
    if self.doc1:
      self.doc1.close()
    self.doc1 = fitz.open(path)
    self.current_page = 0
    self.refresh_view()

  def load_right_pdf(self, path: str):
    if self.doc2:
      self.doc2.close()
    self.doc2 = fitz.open(path)
    self.current_page = 0
    self.refresh_view()

  def set_mode(self, mode: str):
    self.mode = mode
    self.refresh_view()

  def change_zoom(self, delta: float):
    new_zoom = round(max(0.6, min(3.0, self.zoom + delta)), 2)
    if new_zoom != self.zoom:
      self.zoom = new_zoom
      pct = int((self.zoom / 1.4) * 100)
      self.zoom_lbl.setText(f"{pct}%")
      self.refresh_view()

  def max_pages(self) -> int:
    c1 = len(self.doc1) if self.doc1 else 0
    c2 = len(self.doc2) if self.doc2 else 0
    return max(c1, c2)

  def go_to_page(self, page_idx: int):
    total = self.max_pages()
    if 0 <= page_idx < total:
      self.current_page = page_idx
      self.refresh_view()

  def jump_to_next_diff(self):
    if not self.doc1 or not self.doc2:
      return
    total = self.max_pages()
    for offset in range(1, total + 1):
      idx = (self.current_page + offset) % total
      if self._page_has_diff(idx):
        self.go_to_page(idx)
        return
    self.stats_lbl.setText("No differences found across any pages!")

  def _page_has_diff(self, page_idx: int) -> bool:
    if page_idx >= len(self.doc1) or page_idx >= len(self.doc2):
      return True
    p1, p2 = self.doc1[page_idx], self.doc2[page_idx]
    if self.mode in ("text", "both"):
      if p1.get_text("text").strip() != p2.get_text("text").strip():
        return True
    if self.mode in ("pixel", "both"):
      arr1 = self._render_page_np(p1, scale=0.8)
      arr2 = self._render_page_np(p2, scale=0.8)
      if len(self._compute_pixel_boxes(arr1, arr2)) > 0:
        return True
    return False

  # ================= DIFF & RENDERING ENGINE =================
  @staticmethod
  def _render_page_np(page: fitz.Page, scale: float) -> np.ndarray:
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    )
    return arr.copy()

  @staticmethod
  def _merge_word_boxes(
      words: list, indices: range, scale: float
  ) -> list[tuple[float, float, float, float]]:
    """Groups consecutive changed words on the same block & line into clean rectangles."""
    if not indices:
      return []
    merged = []
    cur_x0, cur_y0, cur_x1, cur_y1 = words[indices[0]][:4]
    cur_block, cur_line = words[indices[0]][5], words[indices[0]][6]

    for idx in indices[1:]:
      x0, y0, x1, y1, _, block_no, line_no, _ = words[idx]
      if block_no == cur_block and line_no == cur_line:
        cur_x0 = min(cur_x0, x0)
        cur_y0 = min(cur_y0, y0)
        cur_x1 = max(cur_x1, x1)
        cur_y1 = max(cur_y1, y1)
      else:
        merged.append(
            (cur_x0 * scale, cur_y0 * scale, cur_x1 * scale, cur_y1 * scale)
        )
        cur_x0, cur_y0, cur_x1, cur_y1 = x0, y0, x1, y1
        cur_block, cur_line = block_no, line_no

    merged.append(
        (cur_x0 * scale, cur_y0 * scale, cur_x1 * scale, cur_y1 * scale)
    )
    return merged

  def _compute_text_boxes(self, p1: fitz.Page, p2: fitz.Page, scale: float):
    words1 = p1.get_text("words")  # (x0, y0, x1, y1, "word", block, line, word_idx)
    words2 = p2.get_text("words")

    seq1 = [w[4] for w in words1]
    seq2 = [w[4] for w in words2]

    matcher = difflib.SequenceMatcher(None, seq1, seq2, autojunk=False)
    boxes_left = []
    boxes_right = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
      if tag == "equal":
        continue
      if tag in ("delete", "replace"):
        boxes_left.extend(self._merge_word_boxes(words1, range(i1, i2), scale))
      if tag in ("insert", "replace"):
        boxes_right.extend(self._merge_word_boxes(words2, range(j1, j2), scale))

    return boxes_left, boxes_right

  @staticmethod
  def _compute_pixel_boxes(
      img1: np.ndarray, img2: np.ndarray
  ) -> list[tuple[float, float, float, float]]:
    h = max(img1.shape[0], img2.shape[0])
    w = max(img1.shape[1], img2.shape[1])

    # Pad images to equal size if dimensions differ
    pad1 = np.full((h, w, 3), 255, dtype=np.uint8)
    pad2 = np.full((h, w, 3), 255, dtype=np.uint8)
    pad1[: img1.shape[0], : img1.shape[1]] = img1
    pad2[: img2.shape[0], : img2.shape[1]] = img2

    g1 = cv2.cvtColor(pad1, cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(pad2, cv2.COLOR_RGB2GRAY)

    diff = cv2.absdiff(g1, g2)
    _, thresh = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)

    # Dilate nearby changed pixels into clean grouped regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 9))
    dilated = cv2.dilate(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    boxes = []
    for cnt in contours:
      x, y, bw, bh = cv2.boundingRect(cnt)
      if bw * bh > 35:  # Ignore tiny sub-pixel rendering artifacts
        boxes.append((float(x), float(y), float(x + bw), float(y + bh)))
    return boxes

  @staticmethod
  def _np_to_annotated_pixmap(
      arr: np.ndarray,
      boxes_with_colors: list[tuple[tuple[float, float, float, float], QColor]],
  ) -> QPixmap:
    h, w, ch = arr.shape
    qimg = QImage(arr.data, w, h, ch * w, QImage.Format.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)

    if not boxes_with_colors:
      return pixmap

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pad = 3.0
    for (x0, y0, x1, y1), base_color in boxes_with_colors:
      fill_color = QColor(
          base_color.red(), base_color.green(), base_color.blue(), 48
      )
      border_color = QColor(
          base_color.red(), base_color.green(), base_color.blue(), 230
      )

      pen = QPen(border_color, 2.0)
      painter.setPen(pen)
      painter.setBrush(fill_color)

      rect = QRectF(
          x0 - pad, y0 - pad, (x1 - x0) + pad * 2, (y1 - y0) + pad * 2
      )
      painter.drawRoundedRect(rect, 4.0, 4.0)

    painter.end()
    return pixmap

  def refresh_view(self):
    total = self.max_pages()
    self.page_lbl.setText(
        f"Page {self.current_page + 1 if total else 0} / {total}"
    )
    self.prev_btn.setEnabled(self.current_page > 0)
    self.next_btn.setEnabled(self.current_page < total - 1)
    self.next_diff_btn.setEnabled(bool(self.doc1 and self.doc2 and total > 0))

    # Handle single-side preview before both files are loaded
    if self.doc1 and not self.doc2:
      arr1 = self._render_page_np(self.doc1[self.current_page], self.zoom)
      self.left_pane.scroll_area.set_pixmap(
          self._np_to_annotated_pixmap(arr1, [])
      )
      self.stats_lbl.setText("Now load Modified PDF on the right")
      return
    if self.doc2 and not self.doc1:
      arr2 = self._render_page_np(self.doc2[self.current_page], self.zoom)
      self.right_pane.scroll_area.set_pixmap(
          self._np_to_annotated_pixmap(arr2, [])
      )
      self.stats_lbl.setText("Now load Original PDF on the left")
      return
    if not self.doc1 or not self.doc2:
      return

    has_p1 = self.current_page < len(self.doc1)
    has_p2 = self.current_page < len(self.doc2)

    # Handle missing page when page counts differ
    if not has_p1:
      self.left_pane.scroll_area.set_message(
          f"Page {self.current_page + 1} does not exist in Original PDF"
      )
      arr2 = self._render_page_np(self.doc2[self.current_page], self.zoom)
      box = [(0, 0, arr2.shape[1], arr2.shape[0])]
      self.right_pane.scroll_area.set_pixmap(
          self._np_to_annotated_pixmap(arr2, [(box[0], QColor("#2EA043"))])
      )
      self.stats_lbl.setText("Entire page added in Modified PDF")
      return

    if not has_p2:
      arr1 = self._render_page_np(self.doc1[self.current_page], self.zoom)
      box = [(0, 0, arr1.shape[1], arr1.shape[0])]
      self.left_pane.scroll_area.set_pixmap(
          self._np_to_annotated_pixmap(arr1, [(box[0], QColor("#F85149"))])
      )
      self.right_pane.scroll_area.set_message(
          f"Page {self.current_page + 1} was removed in Modified PDF"
      )
      self.stats_lbl.setText("Entire page removed in Modified PDF")
      return

    # Both pages exist -> Compare!
    p1 = self.doc1[self.current_page]
    p2 = self.doc2[self.current_page]
    arr1 = self._render_page_np(p1, self.zoom)
    arr2 = self._render_page_np(p2, self.zoom)

    left_overlays = []
    right_overlays = []
    diff_count = 0

    if self.mode in ("pixel", "both"):
      px_boxes = self._compute_pixel_boxes(arr1, arr2)
      purple = QColor("#A855F7")
      for b in px_boxes:
        left_overlays.append((b, purple))
        right_overlays.append((b, purple))
      diff_count += len(px_boxes)

    if self.mode in ("text", "both"):
      txt_left, txt_right = self._compute_text_boxes(p1, p2, self.zoom)
      red = QColor("#F85149")
      green = QColor("#2EA043")
      for b in txt_left:
        left_overlays.append((b, red))
      for b in txt_right:
        right_overlays.append((b, green))
      diff_count += len(txt_left) + len(txt_right)

    self.left_pane.scroll_area.set_pixmap(
        self._np_to_annotated_pixmap(arr1, left_overlays)
    )
    self.right_pane.scroll_area.set_pixmap(
        self._np_to_annotated_pixmap(arr2, right_overlays)
    )

    if diff_count == 0:
      self.stats_lbl.setStyleSheet(
          "font-size: 13px; color: #3FB950; font-weight: 600;"
      )
      self.stats_lbl.setText("✓ Pages match in current mode")
    else:
      self.stats_lbl.setStyleSheet(
          "font-size: 13px; color: #F0883E; font-weight: 600;"
      )
      self.stats_lbl.setText(f"Found {diff_count} highlighted region(s) on page")


if __name__ == "__main__":
  app = QApplication(sys.argv)
  app.setStyleSheet(MODERN_QSS)
  window = PDFDiffStudio()
  window.show()
  sys.exit(app.exec())