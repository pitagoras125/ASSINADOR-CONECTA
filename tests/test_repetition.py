import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from reportlab.pdfgen import canvas
from pypdf import PdfReader
from engine import sign_pdf,inspect_pdf
from declaration import make_declaration
from repetition import parse_pages,plan
from test_engine import material

def pages(tmp_path):
    p=tmp_path/'pages.pdf';c=canvas.Canvas(str(p))
    for i in range(3):c.drawString(50,700,f'Original page {i+1}');c.showPage()
    c.save();return p

def test_selection_and_atomic_failure(tmp_path):
    assert parse_pages('3,1-2,2',3)==[0,1,2]
    for text in ('','0','4','3-1','1,,2','1-3-4'):
        with pytest.raises(ValueError):parse_pages(text,3)
    p=pages(tmp_path);out=tmp_path/'invalid.pdf'
    with pytest.raises(ValueError):make_declaration(p,out,'TESTE USUARIO','52998224725','01/01/1990',page_index=0,box=(20,20,400,130),pages='1,4')
    assert not out.exists()

def test_manual_repeat_and_rubrics(tmp_path):
    p=pages(tmp_path);out=tmp_path/'manual.pdf'
    make_declaration(p,out,'TESTE USUARIO','52998224725','01/01/1990',page_index=2,box=(20,20,400,135),pages='1-3',rubrics=True)
    r=PdfReader(out);assert len(r.pages)==3
    assert 'RUBRICA ASSINADOR CONECTA' in r.pages[0].extract_text()
    assert 'CHANCELA ASSINADOR CONECTA' in r.pages[2].extract_text()
    records=r.trailer['/Root']['/ConectaPlacements'];assert len(records)==3
    assert float(records[0]['/Rect'][2])-float(records[0]['/Rect'][0])<float(records[2]['/Rect'][2])-float(records[2]['/Rect'][0])
    for i,page in enumerate(r.pages):assert f'Original page {i+1}' in page.extract_text()
    assert not inspect_pdf(out)

def test_certificate_repeat_and_cosign(material):
    _,pfx,d=material;p=pages(d);out=d/'digital.pdf';next_=d/'next.pdf'
    results=sign_pdf(p,out,pfx,'test-password',page_index=2,box=(20,20,400,135),pages='1-3',rubrics=True)
    assert len(results)==3 and all(x['valid'] and x['intact'] and x['allowed'] for x in results)
    r=PdfReader(out);assert all(len(page['/Annots'])==1 for page in r.pages)
    results=sign_pdf(out,next_,pfx,'test-password',page_index=1,box=(20,200,400,315))
    assert len(results)==4 and all(x['valid'] and x['intact'] and x['allowed'] for x in results)
    assert next_.read_bytes().startswith(out.read_bytes())

def test_dialog_restores_choices_and_page_position(tmp_path):
    from PySide6.QtWidgets import QApplication
    from ui_features import PositionDialog
    app=QApplication.instance() or QApplication([])
    initial=dict(page_index=0,box=(20,20,400,135),pages='1-3',rubrics=True)
    d=PositionDialog(pages(tmp_path),initial=initial)
    assert d.scope.currentIndex()==2 and d.pages_text.text()=='1-3'
    d.rect=[50,100,380,115];d.page.setValue(2);d.page.setValue(1)
    assert d.rect==[50,100,380,115]
    d.confirm();assert d.chosen['pages']=='1-3' and d.chosen['rubrics']
