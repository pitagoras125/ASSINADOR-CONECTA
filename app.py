"""Conecta PDF 0.9 — leitor PDF e NF-e 55."""
import sys, shutil, tempfile
from pathlib import Path
from PySide6.QtCore import Qt,QSettings,QSize,QUrl
from PySide6.QtGui import QIcon,QImage,QPixmap,QPainter,QKeySequence,QShortcut,QColor
from PySide6.QtWidgets import (QApplication,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QFrame,QScrollArea,QTextEdit,QListWidget,QListWidgetItem,QTabBar,QComboBox,QLineEdit,QFileDialog,QMessageBox,QDialog,QGraphicsBlurEffect)
from legacy_ui import Window as SigningWindow
import pypdfium2 as pdfium

class Window(SigningWindow):
    def __init__(self):
        args=sys.argv[:];sys.argv=sys.argv[:1]
        self.ready=False
        super().__init__();sys.argv=args
        self.setWindowTitle('Conecta PDF');self.resize(1450,900);self.setMinimumSize(1120,700)
        self.settings=QSettings('Conecta','Assinador');self.temp=tempfile.TemporaryDirectory(prefix='conecta-')
        self.documents=[];self.active=-1;self.zoom_factor=None;self.rotation=0;self.search_cursor=(-1,-1)
        self.setAcceptDrops(True)
        from ui_shell import build_shell
        self.fit_page=True
        root=build_shell(self)
        self.blur=QGraphicsBlurEffect();self.blur.setEnabled(False);self.blur.setBlurRadius(3);root.setGraphicsEffect(self.blur)
        self.dialog.setFixedWidth(650);self.cert_choice.setText('Assinar com Certificado Digital');self.cpf_choice.setText('Assinar com CPF')
        self.ready=True;self.home()
        self.birth.setInputMask('00/00/0000;_')
        from update_ui import Updates
        self.updates=Updates(self)
        for seq,fn in [('Ctrl+O',self.open_pdf),('Ctrl+S',self.save_pdf),('Ctrl+P',self.print_pdf),('Ctrl+F',self.toggle_search)]:QShortcut(QKeySequence(seq),self,activated=fn)
        for path in args[1:]:
            if not path.startswith('-'):self.load(path)
    def toggle_search(self):
        self.search_bar.show();self.query.setFocus()
    def show_details(self):
        if not self.report.toPlainText() and self.active>=0:
            doc=self.documents[self.active];text='Arquivo: '+doc['source']
            if doc['meta']:text+='\n\nNF-e modelo 55. XML original preservado.\nAssinatura do XML e situação atual na SEFAZ não verificadas.'
            else:text+='\n\nClique em Verificar assinaturas para conferir a integridade criptográfica.'
            self.report.setPlainText(text)
        self.details_dialog.show();self.details_dialog.raise_()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if getattr(self,'ready',False) and self.pdf:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(80,lambda:self.render() if self.pdf else None)
    def button(self,layout,text,callback,style=None):
        b=QPushButton(text);b.clicked.connect(callback)
        if style:b.setObjectName(style)
        layout.addWidget(b);self.actions.append(b);return b
    def busy(self):return bool(self.job and self.job.isRunning())
    def open_url(self,url):
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))
    def home(self):
        if self.pdf:return
        self.image.setText('Seus documentos, em um só lugar\n\nArraste um PDF ou XML de NF-e modelo 55\nou clique em Abrir para começar.')
    def preferences(self):
        box=QMessageBox(self);box.setWindowTitle('Configurações');box.setText('Conecta PDF 1.1.0\nDESENVOLVIDO POR AVANTE SISTEMAS LTDA\nCNPJ 54.713.453/0001-94\n\nPara usar como leitor padrão, instale o aplicativo e escolha Conecta PDF nas configurações de aplicativos padrão do Windows.\n\nOs arquivos são processados localmente. CPF é um registro declaratório, sem autenticação de identidade.');box.addButton('Fechar',QMessageBox.ButtonRole.RejectRole)
        clear=box.addButton('Limpar recentes',QMessageBox.ButtonRole.ActionRole)
        updates=box.addButton('Verificar atualizações',QMessageBox.ButtonRole.ActionRole)
        toggle=box.addButton('Desativar atualizações automáticas' if self.settings.value('automatic_updates',True,type=bool) else 'Ativar atualizações automáticas',QMessageBox.ButtonRole.ActionRole)
        default=box.addButton('Aplicativos padrão',QMessageBox.ButtonRole.ActionRole);default.setEnabled(sys.platform=='win32');box.exec()
        if box.clickedButton()==updates:self.updates.check(manual=True)
        elif box.clickedButton()==toggle:self.settings.setValue('automatic_updates',not self.settings.value('automatic_updates',True,type=bool))
        elif box.clickedButton()==clear:self.settings.remove('recent')
        elif box.clickedButton()==default:self.open_url('ms-settings:defaultapps')
    def recent(self):
        dialog=QDialog(self);dialog.setWindowTitle('Documentos recentes');dialog.resize(640,380);layout=QVBoxLayout(dialog);lst=QListWidget();layout.addWidget(lst)
        for p in self.settings.value('recent',[],type=list):lst.addItem(p)
        lst.itemDoubleClicked.connect(lambda item:(dialog.accept(),self.load(item.text())))
        dialog.exec()
    def open_batch(self):
        from ui_features import BatchFilesDialog
        dialog=BatchFilesDialog(self,self.batch_paths,self.placements)
        if dialog.exec()==QDialog.DialogCode.Accepted and dialog.paths:
            self.load(dialog.paths[0]);self.batch_paths=dialog.paths;self.placements=dialog.placements
            self.label.setText(f'{len(self.batch_paths)} PDFs no lote')
            self.audit_desc.setText('Lote preparado. Escolha o método de assinatura. PDFs já assinados recebem comprovantes separados no modo CPF.')
    def merge_pdfs(self):
        from desktop_tools_ui import organize
        organize(self,'merge')
    def split_pdf(self):
        from desktop_tools_ui import organize
        organize(self,'split')
    def convert_images(self):
        from desktop_tools_ui import organize
        organize(self,'images')
    def scan_document(self):
        from desktop_tools_ui import open_scanner
        open_scanner(self)
    def open_pdf(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Abrir documentos','','Documentos (*.pdf *.xml)')
        self.batch_paths=[]
        for p in paths:self.load(p)
    def load(self,p):
        if not getattr(self,'ready',False):return
        if self.busy():return
        source=Path(p).resolve()
        for i,doc in enumerate(self.documents):
            if doc['source']==str(source):self.tabs.setCurrentIndex(i);self.activate(i);return
        try:
            if source.suffix.lower() not in ('.pdf','.xml','.png','.jpg','.jpeg'):raise ValueError('Escolha um PDF, imagem PNG/JPEG ou XML modelo 55.')
            meta=None;path=str(source)
            if source.suffix.lower()=='.xml':
                from nfe import render_nfe
                import uuid
                path=str(Path(self.temp.name)/(uuid.uuid4().hex+'.pdf'));meta=render_nfe(source,path)
            elif source.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                from PIL import Image
                from reportlab.pdfgen.canvas import Canvas
                from uuid import uuid4
                with Image.open(source) as image:
                    dpi = image.info.get('dpi') or (96, 96)
                    size = tuple(pixels * 72 / max(1, resolution)
                                 for pixels, resolution in zip(image.size, dpi))
                path = str(Path(self.temp.name) / (uuid4().hex + '.pdf'))
                preview = Canvas(path, pagesize=size)
                preview.drawImage(str(source), 0, 0, *size)
                preview.showPage()
                preview.save()
            # Validate before adding tab; close resources promptly.
            candidate=pdfium.PdfDocument(path)
            if not len(candidate):candidate.close();raise ValueError('PDF sem páginas.')
            candidate.close()
            self.documents.append(dict(source=str(source),path=path,meta=meta,page=0))
            self.tabs.blockSignals(True);index=self.tabs.addTab((source.stem[:17]+'…'+source.suffix) if len(source.name)>26 else source.name);self.tabs.setTabToolTip(index,str(source));self.tabs.blockSignals(False);self.tabs.setCurrentIndex(index);self.activate(index)
            if not str(source).startswith(self.temp.name):
                rec=[str(source)]+[x for x in self.settings.value('recent',[],type=list) if x!=str(source)];self.settings.setValue('recent',rec[:15])
        except Exception as exc:QMessageBox.warning(self,'Não foi possível abrir',str(exc))
    def switch_tab(self,index):
        if self.busy():
            self.tabs.blockSignals(True);self.tabs.setCurrentIndex(self.active);self.tabs.blockSignals(False);return
        self.activate(index)
    def activate(self,index):
        if index<0 or index>=len(self.documents):return
        if self.active>=0 and self.active<len(self.documents):self.documents[self.active]['page']=self.page
        if self.pdf:self.pdf.close()
        self.active=index;doc=self.documents[index];self.path=doc['path'];self.pdf=pdfium.PdfDocument(self.path);self.pdf.init_forms();self.page=min(doc['page'],len(self.pdf)-1);self.rotation=0;self.search_cursor=(-1,-1)
        self.status.setStyleSheet('');self.status.setText('Assinatura: não verificada');self.detected.setText('Assinaturas');self.report.clear();self.batch_paths=[]
        if doc['meta']:
            m=doc['meta'];self.audit_desc.setText('NF-e • Modelo 55\nXML original preservado');self.label.setText('DANFE gerado a partir do XML — '+Path(doc['source']).name)
        else:self.audit_desc.setText('Documento PDF\nArquivo original preservado')
        self.thumbs.blockSignals(True);self.thumbs.clear()
        for i in range(len(self.pdf)):
            item=QListWidgetItem(str(i+1));item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if i<150:
                page=self.pdf[i];bitmap=page.render(scale=72/page.get_width());pil=bitmap.to_pil().convert('RGB');im=QImage(pil.tobytes(),pil.width,pil.height,pil.width*3,QImage.Format.Format_RGB888).copy();item.setIcon(QIcon(QPixmap.fromImage(im)));bitmap.close();page.close()
            self.thumbs.addItem(item)
        self.thumbs.setCurrentRow(self.page);self.thumbs.blockSignals(False);self.render()
    def close_tab(self,index):
        if self.busy():return
        if self.pdf:self.pdf.close();self.pdf=None
        self.documents.pop(index);self.active=-1;self.tabs.blockSignals(True);self.tabs.removeTab(index);self.tabs.blockSignals(False)
        if self.documents:self.activate(self.tabs.currentIndex())
        else:self.path=None;self.thumbs.clear();self.pagination.setText('0 / 0');self.image.clear();self.report.clear();self.audit_desc.setText('Abra um PDF ou XML.');self.status.setText('Nenhum documento aberto');self.home()
    def thumbnail_selected(self,row):
        if self.pdf and row>=0:self.page=row;self.render()
    def change_zoom(self,text):
        self.fit_page=text=='Página inteira'
        self.zoom_factor=None if text in ('Ajustar largura','Página inteira') else int(text.rstrip('%'))/100
        if self.pdf:self.render()
    def rotate(self):
        self.rotation=(self.rotation+90)%360
        if self.pdf:self.render()
    def render(self):
        if not self.pdf:return
        page=self.pdf[self.page];width=page.get_height() if self.rotation%180 else page.get_width()
        height=page.get_width() if self.rotation%180 else page.get_height()
        fit_width=(self.scroll.viewport().width()-34)/width
        scale=self.zoom_factor or max(.15,min(2.0,fit_width,(self.scroll.viewport().height()-30)/height if self.fit_page else 2.0))
        bitmap=page.render(scale=scale,rotation=self.rotation,draw_annots=True);pil=bitmap.to_pil().convert('RGB');im=QImage(pil.tobytes(),pil.width,pil.height,pil.width*3,QImage.Format.Format_RGB888).copy();self.image.setPixmap(QPixmap.fromImage(im));bitmap.close();page.close()
        self.pagination.setText(f'{self.page+1} / {len(self.pdf)}');self.thumbs.blockSignals(True);self.thumbs.setCurrentRow(self.page);self.thumbs.blockSignals(False)
        name=Path(self.documents[self.active]['source']).name if self.active>=0 else Path(self.path).name
        self.label.setText(name+'  •  '+str(len(self.pdf))+' página(s)  •  Processamento local')
    def find_text(self):
        if not self.pdf or not self.query.text().strip():return
        needle=self.query.text().casefold();start=self.search_cursor[0]+1 if self.search_cursor[1]==needle else self.page
        for offset in range(len(self.pdf)):
            i=(start+offset)%len(self.pdf);page=self.pdf[i];text=page.get_textpage();content=text.get_text_range();text.close();page.close()
            if needle in content.casefold():self.page=i;self.search_cursor=(i,needle);self.render();self.label.setText(f'Texto encontrado na página {i+1}.');return
        QMessageBox.information(self,'Pesquisa','Texto não encontrado. PDFs digitalizados podem precisar de OCR.')
    def output_source(self):
        return self.documents[self.active]['source'] if self.active>=0 else self.path
    def save_pdf(self):
        if not self.path:return
        doc=self.documents[self.active];suggestion=Path(doc['source']).stem+'.pdf'
        out,_=QFileDialog.getSaveFileName(self,'Salvar cópia PDF',str(Path(doc['source']).parent/suggestion),'PDF (*.pdf)')
        if not out:return
        if not out.lower().endswith('.pdf'):out+='.pdf'
        try:
            if Path(out).exists():raise ValueError('Escolha um nome novo. Os arquivos existentes são preservados.')
            with open(out,'xb') as f:f.write(Path(self.path).read_bytes())
            self.label.setText('Cópia salva: '+out)
        except Exception as exc:QMessageBox.warning(self,'Salvar PDF',str(exc))
    def print_pdf(self):
        if not self.pdf:return
        from PySide6.QtPrintSupport import QPrinter,QPrintDialog
        printer=QPrinter(QPrinter.PrinterMode.HighResolution);dialog=QPrintDialog(printer,self)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        painter=QPainter()
        if not painter.begin(printer):QMessageBox.warning(self,'Impressão','Não foi possível iniciar a impressora.');return
        try:
            first=max(0,printer.fromPage()-1);last=min(len(self.pdf),printer.toPage() or len(self.pdf))
            for i in range(first,last):
                if i>first:printer.newPage()
                page=self.pdf[i];bitmap=page.render(scale=2.5,draw_annots=True);pil=bitmap.to_pil().convert('RGB');im=QImage(pil.tobytes(),pil.width,pil.height,pil.width*3,QImage.Format.Format_RGB888).copy();rect=printer.pageRect(QPrinter.Unit.DevicePixel).toRect();size=im.size().scaled(rect.size(),Qt.AspectRatioMode.KeepAspectRatio);rect.setSize(size);painter.drawImage(rect,im);bitmap.close();page.close()
        finally:painter.end()
    def open_signing(self):
        if self.busy():return
        if not self.path:
            QMessageBox.information(self,'Abrir documento','Abra um PDF ou XML antes de assinar.');return
        self.advanced=False
        self.cert_choice.setChecked(False);self.cpf_choice.setChecked(False)
        self.form.hide();self.sign.setEnabled(False);self.sign.hide()
        self.blur.setEnabled(True);self.overlay.setGeometry(self.centralWidget().geometry());self.overlay.show();self.overlay.raise_()
        self.dialog.adjustSize();self.dialog.move(self.mapToGlobal(self.rect().center())-self.dialog.rect().center());self.dialog.show();self.dialog.raise_();self.dialog.activateWindow()
    def select_method(self,index):
        super().select_method(index)
        self.sign.show();self.dialog.adjustSize()
        self.dialog.move(self.mapToGlobal(self.rect().center())-self.dialog.rect().center())
    def open_method(self,method):
        if self.busy():return
        self.open_signing()
        if self.path:self.select_method(method)
    def sign_document(self):
        if self.signing_mode()==2 and self.path and not self.batch_paths:
            from engine import inspect_pdf
            try:signed=bool(inspect_pdf(self.path))
            except Exception as exc:QMessageBox.warning(self,'Documento',str(exc));return
            if signed:
                out,_=QFileDialog.getSaveFileName(self,'Salvar comprovante separado',str(Path(self.documents[self.active]['source']).with_suffix(''))+'_comprovante_cpf.pdf','PDF (*.pdf)')
                if not out:return
                if not out.lower().endswith('.pdf'):out+='.pdf'
                from cpf_protected import make_protected_declaration
                source=self.path;name=self.name.text();cpf=self.cpf.text();birth=self.birth.text();self.dialog.hide()
                def complete(results):
                    self.name.clear();self.cpf.clear();self.birth.clear();self.report.setPlainText('Comprovante salvo em:\n'+out+'\n\nOriginal preservado byte a byte.\nSHA-256: '+__import__('hashlib').sha256(Path(source).read_bytes()).hexdigest()+'\n\nIdentidade não autenticada. Comprovante protegido por selo técnico local autoassinado.');self.status.setText('Comprovante por CPF criado')
                self.run_job(lambda:make_protected_declaration(source,out,name,cpf,birth),complete);return
        super().sign_document()
    def show_report(self,results):
        super().show_report(results)
        self.show_details()
        if any('SELO LOCAL' in r.get('signer','') for r in results):
            self.audit_desc.setText('Há selo técnico local de integridade. Ele não autentica o CPF nem representa certificado ICP-Brasil. A integridade matemática é verificada separadamente da identidade.')
    def run_job(self,operation,callback):
        def complete(result):
            # Base completion callbacks load generated outputs while worker may still be finishing.
            self.job.wait();callback(result)
        self.tabs.setEnabled(False);super().run_job(operation,complete)
    def finished(self):
        super().finished();self.tabs.setEnabled(True)
    def dragEnterEvent(self,event):
        if not self.busy() and event.mimeData().hasUrls() and all(u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in ('.pdf','.xml') for u in event.mimeData().urls()):event.acceptProposedAction()
    def dropEvent(self,event):
        if not self.busy():
            for u in event.mimeData().urls():self.load(u.toLocalFile())
            event.acceptProposedAction()
    def closeEvent(self,event):
        if self.busy() or (hasattr(self,'updates') and self.updates.worker and self.updates.worker.isRunning()):event.ignore();return
        if hasattr(self,'updates') and not self.updates.install_on_exit():
            event.ignore();return
        if self.pdf:self.pdf.close();self.pdf=None
        self.temp.cleanup();event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv)
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Conecta.AssinadorConecta')
    window=Window()
    if len(sys.argv)==3 and sys.argv[1]=='--print':
        if window.pdf:
            window.print_pdf()
        window.close()
    else:
        window.show()
        sys.exit(app.exec())
