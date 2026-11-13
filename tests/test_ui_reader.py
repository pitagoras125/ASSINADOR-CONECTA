import os,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from app import Window,QApplication,QMessageBox
from test_engine import material
from engine import sign_pdf,inspect_pdf
from PySide6.QtWidgets import QFileDialog

def test_tabs_search_rotation_and_job(material,monkeypatch):
    pdf,pfx,d=material
    application=QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:(_ for _ in ()).throw(AssertionError(a[-1])))
    window=Window();window.show();application.processEvents()
    try:
        window.load(str(pdf));window.load(str(Path(__file__).parent/'fixtures/nfe55.xml'));assert window.tabs.count()==2
        assert window.output_source().endswith('nfe55.xml') and window.path.endswith('.pdf')
        window.tabs.setCurrentIndex(0);window.query.setText('ORIGINAL');window.find_text();assert window.page==0
        window.rotate();assert window.rotation==90
        window.close_tab(1);assert window.tabs.count()==1
        called=[];window.run_job(lambda:42,called.append)
        limit=time.monotonic()+10
        while (window.busy() or not called) and time.monotonic()<limit:application.processEvents();time.sleep(.01)
        application.processEvents();assert called==[42] and window.tabs.isEnabled()
        signed=d/'gui_signed.pdf';sign_pdf(pdf,signed,pfx,'test-password');window.load(str(signed));window.select_method(1)
        window.name.setText('Pessoa Teste');window.cpf.setText('52998224725');window.birth.setText('01/01/1990')
        out=d/'gui_receipt.pdf';monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a,**kw:(str(out),'PDF'))
        window.sign_document();limit=time.monotonic()+20
        while (window.busy() or not out.exists()) and time.monotonic()<limit:application.processEvents();time.sleep(.01)
        application.processEvents();assert out.exists() and inspect_pdf(out)[0]['intact']
        assert window.path==str(signed.resolve())
    finally:window.close();application.processEvents()

def test_scan_completion_displays_saved_files(tmp_path, monkeypatch):
    from PIL import Image
    from reportlab.pdfgen.canvas import Canvas
    from windows_scan_ui import ScannerDialog
    application = QApplication.instance() or QApplication([])
    window = Window()
    outputs = [tmp_path / name for name in ('contrato.pdf', 'folha.png', 'recibo.jpg')]
    pdf = Canvas(str(outputs[0]))
    pdf.drawString(20, 50, 'Contrato')
    pdf.showPage()
    pdf.save()
    for path in outputs[1:]:
        Image.new('RGB', (100, 200), 'blue').save(path)
    def simulate_capture(dialog):
        dialog.saved = outputs
        dialog.success()
        return dialog.result()
    monkeypatch.setattr(ScannerDialog, 'discover', lambda self: None)
    monkeypatch.setattr(ScannerDialog, 'exec', simulate_capture)
    try:
        window.scan_document()
        assert [doc['source'] for doc in window.documents] == list(map(str, outputs))
        assert window.tabs.currentIndex() == 2
        assert not window.image.pixmap().isNull()
    finally:
        window.close()
        application.processEvents()
