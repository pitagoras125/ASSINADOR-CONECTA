import os,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from app import Window
from test_engine import material
from engine import inspect_pdf
from placement import pdf_to_display

def test_inline_drag_resize_and_sign(material,monkeypatch):
    pdf,pfx,folder=material
    application=QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:(_ for _ in ()).throw(AssertionError(a[-1])))
    monkeypatch.setattr(QMessageBox,'information',lambda *a:None)
    w=Window();w.show();application.processEvents()
    try:
        original=pdf.read_bytes();w.load(str(pdf));w.source.setCurrentIndex(1);w.select_method(0)
        w.pfx.setText(str(pfx));w.password.setText('test-password');application.processEvents()
        assert not w.dialog.isVisible() and w.sign.isVisible() and w.form.isVisible()
        w.seal_size.setValue(280);application.processEvents()
        preview=w.image;rect=preview.display_rect()[0];before=list(preview.placement()['box'])
        start=rect.center().toPoint();end=start+QPoint(15,-50)
        QTest.mousePress(preview,Qt.MouseButton.LeftButton,pos=start)
        QTest.mouseMove(preview,end);QTest.mouseRelease(preview,Qt.MouseButton.LeftButton,pos=end);application.processEvents()
        assert preview.placement()['box']!=before
        assert abs(pdf_to_display(preview.g,preview.placement()['box'])[2]-280)<1
        out=folder/'inline_signed.pdf'
        monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**k:(str(out),'PDF'))
        # The inline workflow must not reopen the old placement modal.
        from ui_features import PositionDialog
        monkeypatch.setattr(PositionDialog,'exec',lambda self:(_ for _ in ()).throw(AssertionError('unexpected modal')))
        w.sign_document();limit=time.monotonic()+20
        while (w.busy() or not out.exists()) and time.monotonic()<limit:application.processEvents();time.sleep(.01)
        application.processEvents()
        assert out.exists() and inspect_pdf(out)[0]['intact'] and pdf.read_bytes()==original
        assert w.path==str(out.resolve())
        w.close_tab(w.tabs.currentIndex());w.close_tab(0)
        assert w.path is None and not w.signature_panel.isEnabled()
    finally:w.close();application.processEvents()


def test_full_page_keeps_manual_placement_available(material,monkeypatch):
    pdf,_,_=material
    application=QApplication.instance() or QApplication([])
    w=Window();w.show();application.processEvents();w.load(str(pdf))
    import inline_preview
    monkeypatch.setattr(inline_preview,'choose_placement',lambda *a:(_ for _ in ()).throw(ValueError('Sem espaço livre')))
    try:
        w.select_method(1)
        assert w.image.placement() is not None
        assert w.image.display_rect() is not None
    finally:w.close();application.processEvents()
