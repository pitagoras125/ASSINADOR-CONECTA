from pathlib import Path
import pypdfium2 as pdfium
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QListWidget,QListWidgetItem,QAbstractItemView,QFileDialog,QMessageBox,QInputDialog,QCheckBox)
from pdf_tools import merge_pdfs,extract_pages,images_to_pdf,read_pdf

class OrderedFiles(QDialog):
    def __init__(self,parent,title,paths):
        super().__init__(parent);self.setWindowTitle(title);self.resize(650,450)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Arraste os documentos para definir a ordem.'))
        self.files=QListWidget();self.files.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.files.setIconSize(QSize(120, 144))
        self.files.setDragDropOverwriteMode(False)
        self.files.setSpacing(3)
        self.queue = []
        for path in paths:
            item = QListWidgetItem(Path(path).name, self.files)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.queue.append(item)
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.preview_next)
        self.preview_timer.start(10)
        layout.addWidget(self.files)
        bar=QHBoxLayout();remove=QPushButton('Remover');remove.clicked.connect(lambda:self.files.takeItem(self.files.currentRow()) if self.files.currentRow()>=0 else None);bar.addWidget(remove)
        go=QPushButton('Continuar');go.setObjectName('primary');go.clicked.connect(self.accept);bar.addWidget(go);layout.addLayout(bar)
    def preview_next(self):
        if not self.queue:
            self.preview_timer.stop()
            return
        item = self.queue.pop(0)
        path = item.data(Qt.ItemDataRole.UserRole)
        try:
            if Path(path).suffix.lower() == '.pdf':
                doc = pdfium.PdfDocument(path)
                try:
                    page = doc[0]
                    width, height = page.get_size()
                    bitmap = page.render(scale=min(240/width, 288/height))
                    image = bitmap.to_pil().convert('RGB')
                    pix = QPixmap.fromImage(QImage(image.tobytes(), image.width, image.height,
                                                  image.width*3, QImage.Format.Format_RGB888).copy())
                    item.setText(f'{Path(path).name}  ·  {len(doc)} pág.')
                finally:
                    doc.close()
            else:
                pix = QPixmap(path).scaled(240, 288, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
            item.setIcon(QIcon(pix))
        except Exception:
            item.setText(f'{Path(path).name}  ·  Prévia indisponível')

    @property
    def paths(self):return [self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())]

def save_path(parent,title):
    out,_=QFileDialog.getSaveFileName(parent,title,'','PDF (*.pdf)')
    if out and not out.lower().endswith('.pdf'):out+='.pdf'
    return out

def organize(window,mode):
    if window.busy():return
    try:
        if mode=='split':
            if not window.path:raise ValueError('Abra o PDF que deseja separar.')
            count=len(read_pdf(window.path).pages)
            pages,ok=QInputDialog.getText(window,'Separar PDF',f'Páginas desejadas (1 a {count}), por exemplo 1-3,5:')
            if not ok:return
            out=save_path(window,'Salvar páginas em um novo PDF')
            if out:window.run_job(lambda:extract_pages(window.path,out,pages),window.load)
            return
        is_pdf=mode=='merge';title='Juntar PDFs' if is_pdf else 'Imagens para PDF'
        paths,_=QFileDialog.getOpenFileNames(window,title,'','PDF (*.pdf)' if is_pdf else 'Imagens (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)')
        if not paths:return
        d=OrderedFiles(window,title,paths)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        paths=d.paths;out=save_path(window,'Salvar novo PDF')
        if out:window.run_job(lambda:(merge_pdfs if is_pdf else images_to_pdf)(paths,out),window.load)
    except Exception as exc:QMessageBox.warning(window,'Documento',str(exc))

def open_scanner(window):
    if not window.busy():
        from windows_scan_ui import ScannerDialog
        dialog = ScannerDialog(window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for path in dialog.saved:
                window.load(str(path))
