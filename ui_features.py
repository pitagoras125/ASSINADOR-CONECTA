"""Prévia de posição e seleção de PDFs em lote."""
from pathlib import Path
import io
import pypdfium2 as pdfium
from pypdf import PdfReader
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPixmap,QImage,QPainter,QColor,QPen
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QScrollArea,QSpinBox,QComboBox,QLineEdit,QMessageBox,QListWidget,QFileDialog)
from placement import geometry,display_to_pdf,pdf_to_display,occupied,choose_placement,validate_box


def pixmap(bitmap):
    pil=bitmap.to_pil().convert('RGB');raw=pil.tobytes()
    return QPixmap.fromImage(QImage(raw,pil.width,pil.height,pil.width*3,QImage.Format.Format_RGB888).copy())

class PlacementCanvas(QLabel):
    """Arraste uma área, mova pelo centro e redimensione pelos quatro cantos."""
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.action=None;self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
    def corners(self):
        x,y,w,h=self.owner.rect
        return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
    def handle(self,x,y):
        for i,(a,b) in enumerate(self.corners()):
            if abs(a-x)*self.owner.scale<=9 and abs(b-y)*self.owner.scale<=9:return i
        return None
    def paintEvent(self,event):
        p=QPainter(self);p.drawPixmap(0,0,self.owner.base);s=self.owner.scale
        for box in self.owner.used:
            x,y,w,h=pdf_to_display(self.owner.g,box)
            p.fillRect(QRectF(x*s,y*s,w*s,h*s),QColor(230,65,65,35))
        x,y,w,h=self.owner.rect;target=QRectF(x*s,y*s,w*s,h*s)
        p.drawPixmap(target,self.owner.seal,QRectF(self.owner.seal.rect()))
        p.setPen(QPen(QColor('#00a88b'),2,Qt.PenStyle.DashLine));p.drawRect(target)
        p.setPen(QPen(QColor('#008870'),1));p.setBrush(QColor('white'))
        for a,b in self.corners():p.drawRect(QRectF(a*s-5,b*s-5,10,10))
    def point(self,event):
        return (max(0,min(self.owner.g['width'],event.position().x()/self.owner.scale)),max(0,min(self.owner.g['height'],event.position().y()/self.owner.scale)))
    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        x,y=self.point(event);self.before=list(self.owner.rect);self.start=(x,y)
        corner=self.handle(x,y);a,b,w,h=self.owner.rect
        if corner is not None:
            self.action='resize';self.anchor=self.corners()[(corner+2)%4]
        elif a<=x<=a+w and b<=y<=b+h:self.action='move'
        else:self.action='draw';self.anchor=(x,y)
    def mouseMoveEvent(self,event):
        x,y=self.point(event)
        if self.action=='move':
            a,b,w,h=self.before
            self.owner.rect=[max(0,min(self.owner.g['width']-w,a+x-self.start[0])),max(0,min(self.owner.g['height']-h,b+y-self.start[1])),w,h]
        elif self.action in ('draw','resize'):
            a,b=self.anchor;dx=x-a;dy=y-b;ratio=460/140
            w=min(abs(dx),abs(dy)*ratio);h=w/ratio
            self.owner.rect=[a-w if dx<0 else a,b-h if dy<0 else b,w,h]
        else:
            corner=self.handle(x,y);a,b,w,h=self.owner.rect
            cursor=(Qt.CursorShape.SizeFDiagCursor if corner in (0,2) else Qt.CursorShape.SizeBDiagCursor) if corner is not None else Qt.CursorShape.SizeAllCursor if a<=x<=a+w and b<=y<=b+h else Qt.CursorShape.CrossCursor
            self.setCursor(cursor);return
        self.owner.size_label.setText(f'{self.owner.rect[2]:.0f} × {self.owner.rect[3]:.0f} pt');self.update()
    def mouseReleaseEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton or not self.action:return
        self.mouseMoveEvent(event)
        if min(self.owner.rect[2:])<35:self.owner.rect=self.before
        self.action=None;self.owner.size_label.setText(f'{self.owner.rect[2]:.0f} × {self.owner.rect[3]:.0f} pt');self.update()

class PositionDialog(QDialog):
    def __init__(self,path,parent=None,initial=None,preview_name='NOME DO ASSINANTE',method='cert'):
        super().__init__(parent);self.setWindowTitle('Posicionar chancela • prévia');self.resize(880,730)
        self.path=str(path);self.reader=PdfReader(self.path);self.doc=pdfium.PdfDocument(self.path);self.doc.init_forms();self.chosen=None
        self.setStyleSheet('QDialog{background:#f4f6fa} QLabel{color:#233953} QPushButton{padding:8px 14px;border:1px solid #ccd8e9;border-radius:6px;background:white} QPushButton#apply{background:#080b12;color:white}')
        layout=QVBoxLayout(self);top=QHBoxLayout();layout.addLayout(top)
        top.addWidget(QLabel('Página'));self.page=QSpinBox();self.page.setRange(1,len(self.reader.pages));top.addWidget(self.page)
        top.addSpacing(14);top.addWidget(QLabel('Arraste na página para escolher a área'));top.addStretch()
        self.size_label=QLabel();top.addWidget(self.size_label)
        options=QHBoxLayout();layout.addLayout(options)
        self.scope=QComboBox();self.scope.addItems(['Somente esta página','Todas as páginas','Páginas selecionadas']);options.addWidget(self.scope)
        self.pages_text=QLineEdit();self.pages_text.setPlaceholderText('Ex.: 1,3-5');self.pages_text.setEnabled(False);options.addWidget(self.pages_text)
        self.repeat_style=QComboBox();self.repeat_style.addItems(['Chancela completa em todas','Rubricas + chancela na última selecionada']);options.addWidget(self.repeat_style)
        self.repeat_style.setEnabled(False)
        self.scope.currentIndexChanged.connect(lambda i:(self.pages_text.setEnabled(i==2),self.repeat_style.setEnabled(i!=0)))
        layout.addWidget(QLabel('Com certificado: cada página selecionada recebe uma assinatura digital. Rubricas são chancelas menores, sem imitar assinatura manuscrita.'))
        self.view=PlacementCanvas(self);scroll=QScrollArea();scroll.setWidget(self.view);scroll.setAlignment(Qt.AlignmentFlag.AlignCenter);layout.addWidget(scroll,1)
        layout.addWidget(QLabel('Arraste em uma área livre para definir local e tamanho. Arraste o centro para mover e os cantos para ajustar. Áreas vermelhas indicam assinaturas existentes.\nConfira se o local está livre de texto: a seleção não detecta o conteúdo da página.'))
        buttons=QHBoxLayout();layout.addLayout(buttons);cancel=QPushButton('Cancelar');cancel.clicked.connect(self.reject);buttons.addWidget(cancel);buttons.addStretch();apply=QPushButton('Usar esta posição');apply.setObjectName('apply');apply.clicked.connect(self.confirm);buttons.addWidget(apply)
        from seal import seal_pdf
        sample=seal_pdf(preview_name,'PRÉVIA',method,'PRÉVIA — NÃO ASSINADO','0'*64,'EMISSOR DO CERTIFICADO')
        demo=pdfium.PdfDocument(sample);p=demo[0];b=p.render(scale=1.5);self.seal=pixmap(b);b.close();p.close();demo.close()
        self.initial=initial;self.page_rects={};self.loaded_index=None
        self.page.setValue((initial or {}).get('page_index',len(self.reader.pages)-1)+1)
        self.page.valueChanged.connect(self.load_page)
        self.load_page()
        if initial and initial.get('pages'):
            self.scope.setCurrentIndex(2);self.pages_text.setText(initial['pages']);self.repeat_style.setCurrentIndex(1 if initial.get('rubrics') else 0)
    def load_page(self):
        if self.loaded_index is not None:self.page_rects[self.loaded_index]=list(self.rect)

        index=self.page.value()-1;self.g=geometry(self.reader.pages[index]);self.used=occupied(self.reader,index)
        self.scale=min(1.3,740/self.g['width'],505/self.g['height'])
        page=self.doc[index];b=page.render(scale=self.scale,draw_annots=True);self.base=pixmap(b);b.close();page.close();self.view.setFixedSize(self.base.size())
        maximum=int(min(460,self.g['width']-20,self.g['height']*460/140-20))
        self.view.action=None
        initial=self.initial if self.initial and self.initial['page_index']==index else None
        if index in self.page_rects:self.rect=list(self.page_rects[index])
        elif initial:self.rect=list(pdf_to_display(self.g,initial['box']))
        else:
            try:_,box=choose_placement(self.path,index);self.rect=list(pdf_to_display(self.g,box))
            except ValueError:self.rect=[10,10,maximum,maximum*140/460]
        
        self.loaded_index=index
        self.size_label.setText(f'{int(self.rect[2])} pt');self.view.update()
    def confirm(self):
        index=self.page.value()-1
        try:box=validate_box(self.reader,index,display_to_pdf(self.g,self.rect))
        except ValueError as exc:QMessageBox.warning(self,'Escolha outra área',str(exc));return
        self.chosen=dict(page_index=index,box=box)
        if self.scope.currentIndex()!=0:
            from repetition import plan
            pages=f'1-{len(self.reader.pages)}' if self.scope.currentIndex()==1 else self.pages_text.text()
            rubrics=self.repeat_style.currentIndex()==1
            try:plan(self.path,index,box,pages,rubrics)
            except ValueError as exc:QMessageBox.warning(self,'Confira as páginas',str(exc));return
            self.chosen.update(pages=pages,rubrics=rubrics)
        self.accept()
    def done(self,result):
        self.doc.close();super().done(result)

class BatchFilesDialog(QDialog):
    def __init__(self,parent=None,paths=None,placements=None):
        super().__init__(parent);self.setWindowTitle('Assinatura em lote');self.resize(700,450)
        self.paths=list(paths or []);self.placements=dict(placements or {})
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Selecione os PDFs. Cada original será preservado; os resultados vão para uma pasta escolhida.'))
        self.items=QListWidget();layout.addWidget(self.items,1)
        row=QHBoxLayout();layout.addLayout(row)
        for label,fn in [('Adicionar PDFs',self.add_files),('Remover',self.remove),('Posicionar neste PDF',self.position)]:
            b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        layout.addWidget(QLabel('Sem posição escolhida: o programa usa uma área sem outra chancela no rodapé.\nO lote usa um único método e signatário por execução.'))
        row=QHBoxLayout();layout.addLayout(row);cancel=QPushButton('Cancelar');cancel.clicked.connect(self.reject);row.addWidget(cancel);row.addStretch();ready=QPushButton('Preparar assinaturas');ready.clicked.connect(self.confirm);row.addWidget(ready);self.refresh()
    def refresh(self):
        self.items.clear()
        for path in self.paths:self.items.addItem(Path(path).name+('   • posição escolhida' if str(Path(path).resolve()) in self.placements else '   • automática'))
    def add_files(self):
        files,_=QFileDialog.getOpenFileNames(self,'Adicionar PDFs','','PDF (*.pdf)')
        self.paths=list(dict.fromkeys(self.paths+files));self.refresh()
    def remove(self):
        i=self.items.currentRow()
        if i>=0:self.paths.pop(i);self.refresh()
    def position(self):
        i=self.items.currentRow()
        if i<0:return
        path=self.paths[i];key=str(Path(path).resolve())
        try:dialog=PositionDialog(path,self,self.placements.get(key))
        except Exception as exc:QMessageBox.warning(self,'PDF não disponível',str(exc));return
        if dialog.exec()==QDialog.DialogCode.Accepted:self.placements[key]=dialog.chosen;self.refresh();self.items.setCurrentRow(i)
    def confirm(self):
        if not self.paths:QMessageBox.information(self,'Lote vazio','Adicione pelo menos um PDF.');return
        self.accept()
