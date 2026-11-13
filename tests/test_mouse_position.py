import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from reportlab.pdfgen import canvas
from ui_features import PositionDialog

def test_draw_move_resize_and_confirm(tmp_path):
    app=QApplication.instance() or QApplication([])
    pdf=tmp_path/'page.pdf';c=canvas.Canvas(str(pdf));c.drawString(50,700,'Original');c.save()
    d=PositionDialog(pdf);d.show();app.processEvents();v=d.view;s=d.scale
    def drag(a,b):
        point=lambda q:QPoint(round(q[0]*s),round(q[1]*s))
        QTest.mousePress(v,Qt.MouseButton.LeftButton,pos=point(a));QTest.mouseMove(v,point(b));QTest.mouseRelease(v,Qt.MouseButton.LeftButton,pos=point(b));app.processEvents()
    drag((60,80),(380,200));x,y,w,h=d.rect
    assert abs(x-60)<2 and abs(y-80)<2 and 310<w<325 and abs(w/h-460/140)<.01
    old=list(d.rect);drag((x+w/2,y+h/2),(x+w/2+30,y+h/2+40));assert abs(d.rect[0]-old[0]-30)<3 and abs(d.rect[1]-old[1]-40)<3
    x,y,w,h=d.rect;drag((x+w,y+h),(x+w-80,y+h-25));assert d.rect[2]<w-60 and min(d.rect[2:])>=35
    # A tiny selection restores the previous usable selection.
    before=list(d.rect);drag((20,20),(21,21));assert d.rect==before
    d.confirm();assert d.chosen and d.chosen['page_index']==0
