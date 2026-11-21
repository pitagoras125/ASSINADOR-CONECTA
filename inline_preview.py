"""Preview the existing seal on the reader; commit drag coordinates to the signing engine."""
from pathlib import Path
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QPen,QColor
from PySide6.QtWidgets import QLabel
from pypdf import PdfReader
from placement import geometry,pdf_to_display,display_to_pdf,choose_placement,validate_box

class DocumentPreview(QLabel):
    def __init__(self,window):
        super().__init__();self.window=window;self.seal=None;self.drag=None;self.g=None;self.cache_key=None
        self.setMouseTracking(True)
    def invalidate_seal(self,*_):
        self.seal=None;self.update()
    def sync(self):
        w=self.window
        if not w.path or not w.pdf:return
        key=(w.path,w.page)
        if self.cache_key!=key:
            self.reader=PdfReader(w.path);self.g=geometry(self.reader.pages[w.page]);self.cache_key=key
        w.signature_panel.setEnabled(True)
        w.sign_page.blockSignals(True);w.sign_page.setRange(1,len(w.pdf));w.sign_page.setValue(w.page+1);w.sign_page.blockSignals(False)
        self.update()
    def placement(self):
        w=self.window
        return w.placements.get(str(Path(w.path).resolve())) if w.path else None
    def ensure_placement(self):
        w=self.window
        if not w.path:return
        current=self.placement()
        if not current or current['page_index']!=w.page:
            try:
                _,box=choose_placement(w.path,w.page)
            except ValueError:
                # Keep manual placement available even when existing seals fill the page.
                self.sync()
                width=min(460,self.g['width']-20,(self.g['height']-20)*460/140)
                box=validate_box(self.reader,w.page,display_to_pdf(self.g,[10,10,width,width*140/460]))
            w.placements[str(Path(w.path).resolve())]=dict(page_index=w.page,box=box)
            w.position.setCurrentIndex(1)
        self.sync()
        width=pdf_to_display(self.g,self.placement()['box'])[2]
        w.seal_size.blockSignals(True);w.seal_size.setValue(round(width));w.seal_size.blockSignals(False)
    def display_rect(self):
        current=self.placement();w=self.window
        if not current or not self.g or current['page_index']!=w.page or w.rotation:return None
        pix=self.pixmap()
        if not pix or pix.isNull():return None
        s=pix.width()/self.g['width'];ox=(self.width()-pix.width())/2;oy=(self.height()-pix.height())/2
        x,y,width,height=pdf_to_display(self.g,current['box'])
        return QRectF(ox+x*s,oy+y*s,width*s,height*s),s,ox,oy
    def paintEvent(self,event):
        super().paintEvent(event)
        if not getattr(self.window,'inline_signing',False) or not self.window.visible.isChecked():return
        shown=self.display_rect()
        if shown is None:return
        if self.seal is None:
            import pypdfium2 as pdfium
            from seal import seal_pdf
            from ui_features import pixmap
            sample=seal_pdf(self.window.name.text() or 'NOME DO ASSINANTE','PRÉVIA','cpf' if self.window.signing_mode()==2 else 'cert','PRÉVIA — NÃO ASSINADO','0'*64,'EMISSOR DO CERTIFICADO')
            doc=pdfium.PdfDocument(sample);page=doc[0];bitmap=page.render(scale=1.5);self.seal=pixmap(bitmap);bitmap.close();page.close();doc.close()
        p=QPainter(self);rect=shown[0];p.drawPixmap(rect,self.seal,QRectF(self.seal.rect()));p.setPen(QPen(QColor('#0867ff'),1));p.drawRect(rect);p.setBrush(QColor('white'))
        for point in (rect.topLeft(),rect.topRight(),rect.bottomLeft(),rect.bottomRight()):p.drawRect(QRectF(point.x()-3,point.y()-3,6,6))
        p.end()
    def mousePressEvent(self,event):
        shown=self.display_rect()
        if event.button()==Qt.MouseButton.LeftButton and shown and self.window.visible.isChecked() and shown[0].contains(event.position()) and not self.window.busy():
            self.drag=(event.position(),list(pdf_to_display(self.g,self.placement()['box'])))
        else:super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        shown=self.display_rect()
        if self.drag and shown:
            start,before=self.drag;x,y,width,height=before;s=shown[1]
            x=max(0,min(self.g['width']-width,x+(event.position().x()-start.x())/s));y=max(0,min(self.g['height']-height,y+(event.position().y()-start.y())/s))
            self.placement()['box']=display_to_pdf(self.g,[x,y,width,height]);self.update()
        else:self.setCursor(Qt.CursorShape.SizeAllCursor if shown and shown[0].contains(event.position()) else Qt.CursorShape.ArrowCursor)
    def mouseReleaseEvent(self,event):
        if self.drag:
            self.mouseMoveEvent(event);self.drag=None
            validate_box(self.reader,self.window.page,self.placement()['box'])
        super().mouseReleaseEvent(event)
    def resize_seal(self,width):
        self.ensure_placement()
        if not self.g:return
        current=self.placement();x,y,_,_=pdf_to_display(self.g,current['box']);width=min(width,self.g['width']-20,(self.g['height']-20)*460/140);height=width*140/460
        x=max(0,min(x,self.g['width']-width));y=max(0,min(y,self.g['height']-height));current['box']=display_to_pdf(self.g,[x,y,width,height]);self.update()
