from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QLabel, QRubberBand
from pypdf import PdfReader
from placement import geometry, display_to_pdf, validate_box


class DocumentPreview(QLabel):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.cache_key = None
        self.selecting = False
        self.start = None
        self.band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def invalidate_seal(self, *_):
        self.update()

    def sync(self):
        w = self.window
        if not w.path or not w.pdf:
            self.cancel_selection()
            return
        key = (w.path, w.page, w.rotation)
        if self.cache_key != key:
            self.cancel_selection()
            self.reader = PdfReader(w.path)
            self.g = geometry(self.reader.pages[w.page])
            self.cache_key = key
        w.signature_panel.setEnabled(True)

    def begin_selection(self):
        self.selecting = True
        self.start = None
        self.setFocus()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def cancel_selection(self):
        self.start = None
        self.selecting = False
        self.band.hide()
        self.unsetCursor()
        self.window.statusBar().clearMessage()

    def keyPressEvent(self, event):
        if self.selecting and event.key() == Qt.Key.Key_Escape:
            self.cancel_selection()
        else:
            super().keyPressEvent(event)

    def page_rect(self):
        pix = self.pixmap()
        if pix is None or pix.isNull():
            return QRectF()
        size = pix.deviceIndependentSize()
        return QRectF((self.width()-size.width())/2, (self.height()-size.height())/2,
                      size.width(), size.height())

    def mousePressEvent(self, event):
        if (self.selecting and not self.window.busy() and event.button()==Qt.MouseButton.LeftButton
                and self.page_rect().contains(event.position())):
            self.start = event.position()
        else:
            super().mousePressEvent(event)

    def selection_rect(self, point):
        page = self.page_rect()
        dx = point.x()-self.start.x()
        dy = point.y()-self.start.y()
        available_x = page.right()-self.start.x() if dx>=0 else self.start.x()-page.left()
        available_y = page.bottom()-self.start.y() if dy>=0 else self.start.y()-page.top()
        ratio = 460/140
        width = min(max(abs(dx), abs(dy)*ratio), available_x, available_y*ratio)
        height = width/ratio
        return QRectF(self.start.x() if dx>=0 else self.start.x()-width,
                      self.start.y() if dy>=0 else self.start.y()-height, width, height)

    def mouseMoveEvent(self, event):
        if self.start is None:
            return super().mouseMoveEvent(event)
        self.band.setGeometry(self.selection_rect(event.position()).toAlignedRect())
        self.band.show()

    def mouseReleaseEvent(self, event):
        if self.start is None or event.button()!=Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        rect = self.selection_rect(event.position())
        self.start = None
        self.band.hide()
        page = self.page_rect()
        if page.isEmpty() or not self.window.path:
            self.cancel_selection()
            return
        sx = self.g['width']/page.width()
        sy = self.g['height']/page.height()
        box = display_to_pdf(self.g, [(rect.x()-page.x())*sx, (rect.y()-page.y())*sy,
                                      rect.width()*sx, rect.height()*sy])
        try:
            box = validate_box(self.reader, self.window.page, box)
        except ValueError:
            self.window.statusBar().showMessage('Marque uma área maior para a chancela.')
            return
        self.window.placements[str(Path(self.window.path).resolve())] = dict(page_index=self.window.page, box=box)
        self.window.position.setCurrentIndex(1)
        self.cancel_selection()
        self.window.show_signer()
