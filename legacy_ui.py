import sys
from pathlib import Path
import pypdfium2 as pdfium
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QDesktopServices, QPainter, QPen, QColor, QIcon, QPainterPath
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QPushButton,QLabel,QFileDialog,QMessageBox,QLineEdit,QScrollArea,QTextEdit,QComboBox,QCheckBox,QFrame,QDialog,QListWidget,QListWidgetItem,QGraphicsBlurEffect,QProgressDialog)
from engine import sign_pdf, inspect_pdf

def small_icon(kind='pen',color='#00c79c',size=18,background=None):
    pix=QPixmap(size,size);pix.fill(QColor(background) if background else Qt.GlobalColor.transparent)
    painter=QPainter(pix);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.scale(size/20,size/20);painter.setPen(QPen(QColor(color),1.3));painter.setBrush(Qt.BrushStyle.NoBrush)
    path=QPainterPath()
    if kind=='shield':
        path.moveTo(10,3);path.lineTo(16,5);path.lineTo(15.5,11);path.cubicTo(15,14,12,16,10,17);path.cubicTo(7,15.5,4.5,13,4.5,10);path.lineTo(4,5);path.closeSubpath();painter.drawPath(path);painter.drawLine(7,9,9,11);painter.drawLine(9,11,13,7)
    else:
        path.moveTo(3,3);path.lineTo(12,5);path.lineTo(17,13);path.lineTo(12,18);path.lineTo(5,12);path.closeSubpath();painter.drawPath(path);painter.drawEllipse(8,8,3,3);painter.drawLine(10,10,15,15)
    painter.end();return pix

class Job(QThread):
    done = Signal(object)
    progress = Signal(object)
    failed = Signal(str)
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
    def run(self):
        try: self.done.emit(self.operation())
        except Exception as exc: self.failed.emit(str(exc))
        finally: self.operation = None

class CertificateList(QListWidget):
    def __init__(self):
        super().__init__();self.setMinimumHeight(140);self.setMaximumHeight(190);self.setSpacing(6)
    def setPlaceholderText(self,text):self.setToolTip(text)
    def addItem(self,text,data=None):
        item=QListWidgetItem(text);item.setData(Qt.ItemDataRole.UserRole,data);super().addItem(item)
        if self.count()==1:self.setCurrentRow(0)
    def currentData(self):
        item=self.currentItem();return item.data(Qt.ItemDataRole.UserRole) if item else None

class SignatureDialog(QDialog):
    def hideEvent(self,event):
        self.parent().undim();super().hideEvent(event)

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(str(Path(__file__).parent/'assets'/'app_icon.ico')))
        self.setWindowTitle('Conecta PDF • 1.0.0');self.resize(1150,730);self.setMinimumSize(1020,650)
        self.path=None;self.pdf=None;self.page=0;self.job=None;self.batch_paths=[];self.placements={};self.batch_progress=None
        self.setStyleSheet('''
QMainWindow{background:#eef1f5} QWidget{font-family:'Segoe UI';font-size:11px;color:#233953}
QWidget#surface{background:white} QFrame#header{background:white;border-bottom:1px solid #dfe6ef}
QFrame#toolbar{background:white;border-bottom:1px solid #dfe6ef} QFrame#audit{background:white;border-left:1px solid #dfe6ef}
QFrame#statusCard{background:#f8fafe;border:1px solid #dfe7f2;border-radius:9px}
QPushButton{background:white;border:1px solid #ccd8e9;border-radius:6px;padding:6px 10px;color:#1d3554;font-size:10px}
QPushButton:hover{background:#f4f7fc} QPushButton:disabled{background:#f2f4f8;color:#9aa8bc;border-color:#e4eaf2}
QPushButton#primary{background:#050608;border:1px solid #050608;color:white;font-weight:700;padding:7px 17px;border-radius:9px}
QPushButton#primary:hover{background:#17222e} QPushButton#primary:disabled{background:#d9e0e9;border-color:#d9e0e9;color:#94a1b2}
QPushButton#tab{background:transparent;border:1px solid transparent;border-radius:9px;padding:9px 8px;font-size:10px;font-weight:600}
QPushButton#tab:checked{background:white;border:1px solid #dce5f0;color:#05070b}
QPushButton#link{border:0;background:transparent;color:#70829d;font-family:Consolas;font-size:9px;padding:3px}
QLabel#micro{font-family:Consolas;font-size:9px;color:#8196b5} QLabel#muted{font-size:10px;color:#7589a7}
QLabel#heading{font-size:10px;font-weight:700;color:#132941} QLineEdit,QComboBox{background:white;border:1px solid #dce5ef;border-radius:7px;padding:8px;font-size:11px;min-height:17px}
QLineEdit:focus,QComboBox:focus{border-color:#7ba6d6} QComboBox::drop-down{border:0;width:22px}
QTextEdit{border:1px dashed #dbe5f2;border-radius:10px;background:white;padding:10px;color:#7a8fab;font-size:10px}
QListWidget{background:white;border:0;outline:none} QListWidget::item{padding:13px 12px;background:white;border:1px solid #dde6f0;border-radius:10px;color:#20324c;font-size:10px}
QListWidget::item:selected{background:#f2f6fa;border:1px solid #101c29;color:#142137}
QCheckBox{font-size:10px;spacing:6px;padding:3px} QScrollArea{border:0;background:#f6f8fb}
QScrollBar:vertical{background:#f1f3f6;width:9px} QScrollBar::handle:vertical{background:#c8cdd5;border-radius:4px;min-height:28px}
''')
        root=QWidget();root.setObjectName('surface');self.setCentralWidget(root)
        layout=QVBoxLayout(root);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        header=QFrame();header.setObjectName('header');header.setFixedHeight(44);hl=QHBoxLayout(header);hl.setContentsMargins(16,6,16,6);hl.setSpacing(10)
        mark=QLabel();mark.setFixedSize(135,32);mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from branding import logo_image
        logo=logo_image();data=logo.tobytes();qlogo=QImage(data,logo.width,logo.height,logo.width*3,QImage.Format.Format_RGB888).copy()
        mark.setPixmap(QPixmap.fromImage(qlogo).scaled(135,32,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));hl.addWidget(mark)
        version=QLabel('v1.0.0 (Windows PAdES)');version.setObjectName('micro');hl.addWidget(version);hl.addStretch()
        self.label=QLabel('●  Nenhum documento aberto  |  Aguardando assinatura');self.label.setStyleSheet('background:#f1f5fa;border:1px solid #e3eaf3;border-radius:12px;padding:4px 13px;font-size:10px;color:#607692');hl.addWidget(self.label);hl.addStretch()
        iti=QPushButton('VALIDAR ITI ↗');iti.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://validar.iti.gov.br/')));hl.addWidget(iti);layout.addWidget(header)
        workspace=QHBoxLayout();workspace.setSpacing(0);workspace.setContentsMargins(0,0,0,0);layout.addLayout(workspace,1)
        left=QWidget();lv=QVBoxLayout(left);lv.setContentsMargins(0,0,0,0);lv.setSpacing(0);workspace.addWidget(left,1)
        toolbar=QFrame();toolbar.setObjectName('toolbar');toolbar.setFixedHeight(46);bar=QHBoxLayout(toolbar);bar.setContentsMargins(16,7,16,7);bar.setSpacing(8)
        self.actions=[iti]
        for title,callback in [('↥  Abrir PDF',self.open_pdf),('Lote',self.open_batch),('Posicionar',self.pick_position),('‹',lambda:self.move(-1))]:
            button=QPushButton(title);button.clicked.connect(callback);bar.addWidget(button);self.actions.append(button)
        self.pagination=QLabel('0  /  0');self.pagination.setStyleSheet('color:#2260a5;font-family:Consolas;font-size:10px');bar.addWidget(self.pagination)
        nxt=QPushButton('›');nxt.clicked.connect(lambda:self.move(1));bar.addWidget(nxt);self.actions.append(nxt);bar.addStretch()
        self.launch=QPushButton('ASSINAR DOCUMENTO');self.launch.setIcon(QIcon(small_icon()));self.launch.setObjectName('primary');self.launch.clicked.connect(self.open_signing);bar.addWidget(self.launch);self.actions.append(self.launch);lv.addWidget(toolbar)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True)
        self.image=QLabel('Abra um documento PDF\n\nO arquivo será exibido aqui.');self.image.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop);self.image.setStyleSheet('background:#f5f7fa;color:#9aabc1;padding:28px 18px;font-size:12px');self.scroll.setWidget(self.image);lv.addWidget(self.scroll,1)
        audit=QFrame();audit.setObjectName('audit');audit.setFixedWidth(345);workspace.addWidget(audit);al=QVBoxLayout(audit);al.setContentsMargins(0,0,0,0);al.setSpacing(0)
        top=QWidget();tl=QVBoxLayout(top);tl.setContentsMargins(18,17,18,17);tl.setSpacing(8)
        topbar=QHBoxLayout();heading=QLabel('♢  PAINEL DE AUDITORIA &\n     INTEGRIDADE');heading.setObjectName('heading');topbar.addWidget(heading);topbar.addStretch();tag=QLabel('PAdES\nDisponível');tag.setStyleSheet('background:#edfcf6;border:1px solid #acebd3;border-radius:3px;padding:5px 9px;font-family:Consolas;font-size:9px;color:#009779');topbar.addWidget(tag);tl.addLayout(topbar)
        desc=QLabel('Verificação das assinaturas digitais e das alterações no documento.');desc.setObjectName('muted');desc.setWordWrap(True);tl.addWidget(desc);al.addWidget(top)
        line=QFrame();line.setFrameShape(QFrame.Shape.HLine);line.setStyleSheet('color:#e4eaf2');al.addWidget(line)
        statuswrap=QWidget();sw=QVBoxLayout(statuswrap);sw.setContentsMargins(16,15,16,15)
        card=QFrame();card.setObjectName('statusCard');cv=QVBoxLayout(card);cv.setContentsMargins(12,12,12,12);cv.setSpacing(10)
        row=QHBoxLayout();row.addWidget(QLabel('Status de integridade:'));row.addStretch();self.status=QLabel('● Aguardando assinatura');self.status.setStyleSheet('background:#edf2f8;border-radius:8px;padding:3px 6px;font-size:9px;color:#70849f');row.addWidget(self.status);cv.addLayout(row)
        self.audit_desc=QLabel('Nenhuma assinatura digital verificada neste documento. Abra um PDF para começar.');self.audit_desc.setWordWrap(True);self.audit_desc.setStyleSheet('font-size:10px;color:#567193;line-height:1.5');cv.addWidget(self.audit_desc);sw.addWidget(card);al.addWidget(statuswrap)
        rowwrap=QWidget();rh=QHBoxLayout(rowwrap);rh.setContentsMargins(17,4,17,10);self.detected=QLabel('✓  ASSINATURAS DETECTADAS ( 0 )');self.detected.setObjectName('heading');rh.addWidget(self.detected);rh.addStretch();revalidate=QPushButton('⟳ revalidar');revalidate.setObjectName('link');revalidate.clicked.connect(self.verify);rh.addWidget(revalidate);self.actions.append(revalidate);al.addWidget(rowwrap)
        self.report=QTextEdit();self.report.setReadOnly(True);self.report.setHtml('<p align="center" style="color:#9aabc3"><br/>Nenhuma assinatura detectada.<br/>Abra um PDF e clique em revalidar.</p>');al.addWidget(self.report,1)
        security=QFrame();security.setObjectName('security');security.setStyleSheet('QFrame#security{background:#fcfdff;border-top:1px solid #e4eaf2}');sv=QVBoxLayout(security);sv.setContentsMargins(17,16,17,16);sv.setSpacing(8)
        sec_title=QLabel('♢  SEGURANÇA DO ASSINADOR CONECTA');sec_title.setObjectName('heading');sv.addWidget(sec_title)
        for text in ['◇  Chave privada utilizada pelo Windows','◇  Suporte ao repositório pessoal e arquivo PFX','◇  Senha não gravada em configurações']:
            item=QLabel(text);item.setObjectName('micro');sv.addWidget(item)
        al.addWidget(security)
        footer=QFrame();footer.setFixedHeight(24);footer.setObjectName('footer');footer.setStyleSheet('QFrame#footer{background:white;border-top:1px solid #e0e7f1}');fl=QHBoxLayout(footer);fl.setContentsMargins(16,0,16,0)
        for text in ['● ASSINADOR CONECTA  |  SHA-256','Documentos processados no seu computador']:
            lab=QLabel(text);lab.setObjectName('micro');fl.addWidget(lab);fl.addStretch()
        layout.addWidget(footer)
        self.overlay=QWidget(self);self.overlay.setStyleSheet('background:rgba(8,15,25,145)');self.overlay.hide()
        self.blur=QGraphicsBlurEffect();self.blur.setBlurRadius(4);self.blur.setEnabled(False);root.setGraphicsEffect(self.blur)
        self.dialog=SignatureDialog(self);self.dialog.setWindowFlags(Qt.WindowType.Dialog|Qt.WindowType.FramelessWindowHint);self.dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.dialog.setModal(True);self.dialog.setFixedWidth(520)
        outer=QVBoxLayout(self.dialog);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        shell=QFrame();shell.setObjectName('modalShell');shell.setStyleSheet('QFrame#modalShell{background:#ffffff;border:1px solid #dce4ee;border-radius:14px}');outer.addWidget(shell);dl=QVBoxLayout(shell);dl.setContentsMargins(0,0,0,0);dl.setSpacing(0)
        mh=QWidget();mhl=QHBoxLayout(mh);mhl.setContentsMargins(20,20,20,18);mhl.setSpacing(12);icon=QLabel();icon.setPixmap(small_icon(size=23));icon.setAlignment(Qt.AlignmentFlag.AlignCenter);icon.setFixedSize(31,31);icon.setStyleSheet('background:#050608;color:#00d5aa;border-radius:8px;font-size:23px');mhl.addWidget(icon)
        titles=QVBoxLayout();titles.setSpacing(3);title=QLabel('Escolha o Método de Assinatura');title.setStyleSheet('font-size:13px;font-weight:700;color:#18263c');titles.addWidget(title);sub=QLabel('Selecione como deseja assinar o documento');sub.setObjectName('muted');titles.addWidget(sub);mhl.addLayout(titles,1);close=QPushButton('×');close.setObjectName('link');close.clicked.connect(self.dialog.hide);mhl.addWidget(close);dl.addWidget(mh)
        tabs=QWidget();tabs.setObjectName('methodTabs');tabs.setStyleSheet('QWidget#methodTabs{background:#f3f6fa;border-top:1px solid #e4ebf4;border-bottom:1px solid #e4ebf4}');choices=QHBoxLayout(tabs);choices.setContentsMargins(8,7,8,7);choices.setSpacing(8)
        self.cert_choice=QPushButton('Certificado Digital');self.cert_choice.setIcon(QIcon(small_icon('shield')));self.cpf_choice=QPushButton('Chancela Eletrônica (CPF)');self.cpf_choice.setIcon(QIcon(small_icon(color='#647b98')))
        for button in [self.cert_choice,self.cpf_choice]:button.setObjectName('tab');button.setCheckable(True);choices.addWidget(button,1)
        self.cert_choice.clicked.connect(lambda:self.select_method(0));self.cpf_choice.clicked.connect(lambda:self.select_method(1));dl.addWidget(tabs)
        self.mode=QComboBox(self.dialog);self.mode.addItems(['Certificado','CPF']);self.mode.hide()
        self.form=QWidget();form_layout=QVBoxLayout(self.form);form_layout.setContentsMargins(21,18,21,19);form_layout.setSpacing(10);dl.addWidget(self.form)
        certrow=QHBoxLayout();self.cert_heading=QLabel('▱  Certificados encontrados no Windows:');certrow.addWidget(self.cert_heading);certrow.addStretch();self.refresh=QPushButton('⟳ reescanear repositório');self.refresh.setObjectName('link');self.refresh.clicked.connect(self.refresh_certs);certrow.addWidget(self.refresh);form_layout.addLayout(certrow)
        self.certs=CertificateList();self.certs.setMinimumHeight(170);self.certs.setMaximumHeight(190);self.certs.setPlaceholderText('Selecione um certificado');form_layout.addWidget(self.certs)
        self.source=QComboBox();self.source.addItems(['Certificados disponíveis no Windows','Arquivo de certificado (.pfx / .p12)']);self.source.hide();form_layout.addWidget(self.source)
        self.cert_label=QLabel('Arquivo do certificado');form_layout.addWidget(self.cert_label);self.pfx=QLineEdit();self.pfx.setReadOnly(True);form_layout.addWidget(self.pfx)
        self.choose=QPushButton('Selecionar arquivo PFX');self.choose.clicked.connect(self.choose_pfx);form_layout.addWidget(self.choose)
        self.password=QLineEdit();self.password.setEchoMode(QLineEdit.EchoMode.Password);self.password.setPlaceholderText('Senha do certificado');form_layout.addWidget(self.password)
        self.name=QLineEdit();self.name.setPlaceholderText('Nome completo');form_layout.addWidget(self.name);self.cpf=QLineEdit();self.cpf.setPlaceholderText('CPF');form_layout.addWidget(self.cpf);self.birth=QLineEdit();self.birth.setPlaceholderText('Data de nascimento • DD/MM/AAAA');form_layout.addWidget(self.birth)
        self.options=QPushButton('Opções de assinatura ›');self.options.setObjectName('link');self.options.clicked.connect(self.toggle_options);form_layout.addWidget(self.options,0,Qt.AlignmentFlag.AlignLeft)
        self.visible=QCheckBox('Exibir chancela no documento');self.visible.setChecked(True);form_layout.addWidget(self.visible);self.position=QComboBox();self.position.addItems(['Rodapé • automático','Posição escolhida com o mouse']);form_layout.addWidget(self.position);self.coords=QLineEdit();self.coords.setReadOnly(True);self.coords.setPlaceholderText('Use Posicionar para escolher a chancela');form_layout.addWidget(self.coords)
        self.mouse_button=QPushButton('Escolher posição no documento');self.mouse_button.clicked.connect(self.pick_position);form_layout.addWidget(self.mouse_button)
        self.reason=QLineEdit('Assinatura de documento',self.dialog);self.reason.hide();self.info=QLabel();self.info.setWordWrap(True);self.info.setStyleSheet('background:#f7f9fc;border:1px solid #e0e7f1;border-radius:8px;padding:12px;font-size:10px;color:#526b8c');form_layout.addWidget(self.info)
        bottom=QFrame();bottom.setObjectName('modalFooter');bottom.setStyleSheet('QFrame#modalFooter{background:#f7f9fb;border-top:1px solid #e2e9f2;border-bottom-left-radius:14px;border-bottom-right-radius:14px}');buttons=QHBoxLayout(bottom);buttons.setContentsMargins(20,17,20,17)
        auditlabel=QLabel('ASSINADOR CONECTA');auditlabel.setObjectName('micro');buttons.addWidget(auditlabel);buttons.addStretch();cancel=QPushButton('Cancelar');cancel.clicked.connect(self.dialog.hide);buttons.addWidget(cancel);self.sign=QPushButton('Confirmar e Assinar');self.sign.setIcon(QIcon(small_icon()));self.sign.setObjectName('primary');self.sign.clicked.connect(self.sign_document);buttons.addWidget(self.sign);dl.addWidget(bottom)
        self.advanced=False;self.mode.currentIndexChanged.connect(self.update_mode);self.source.currentIndexChanged.connect(self.update_mode);self.position.currentIndexChanged.connect(self.position_changed)
        self.update_mode();self.cert_choice.setChecked(True)
        if len(sys.argv)>1:self.load(sys.argv[1])
    def undim(self):
        self.blur.setEnabled(False);self.overlay.hide()
    def toggle_options(self):
        self.advanced=not self.advanced;self.update_mode();self.dialog.adjustSize()
    def open_signing(self):
        if not self.path:QMessageBox.information(self,'Abrir documento','Abra um PDF antes de assinar.');return
        self.advanced=False;self.select_method(0)
        self.blur.setEnabled(True);self.overlay.setGeometry(self.centralWidget().geometry());self.overlay.show();self.overlay.raise_()
        self.dialog.adjustSize();self.dialog.move(self.mapToGlobal(self.rect().center())-self.dialog.rect().center());self.dialog.show();self.dialog.raise_();self.dialog.activateWindow()
    def select_method(self,index):
        self.mode.setCurrentIndex(index);self.cert_choice.setChecked(index==0);self.cpf_choice.setChecked(index==1)
        self.form.show();self.sign.setEnabled(True);self.update_mode();self.dialog.adjustSize()
        if index==0 and self.source.currentIndex()==0 and sys.platform=='win32':self.refresh_certs()
    def signing_mode(self):
        return 2 if self.mode.currentIndex()==1 else self.source.currentIndex()
    def position_changed(self,index):
        if index==0 and self.path:self.placements.pop(str(Path(self.path).resolve()),None)
        self.update_mode()
    def update_mode(self):
        mode=self.signing_mode()
        self.certs.setVisible(mode==0);self.refresh.setVisible(mode==0);self.cert_heading.setVisible(mode==0)
        for w in [self.cert_label,self.pfx,self.choose,self.password]:w.setVisible(mode==1)
        for w in [self.name,self.cpf,self.birth]:w.setVisible(mode==2)
        self.source.setVisible(mode!=2 and self.advanced)
        self.options.setVisible(mode!=2)
        for w in [self.visible,self.position]:w.setVisible(mode!=2 and self.advanced)
        self.coords.hide();self.mouse_button.setVisible(True)
        self.info.setText('CPF e nascimento declarados. Selo técnico local detecta alterações; não autentica a identidade e não é ICP-Brasil. PDFs já assinados recebem comprovante separado.' if mode==2 else 'A chave privada é utilizada pelo Windows. O provedor pode solicitar autorização ou PIN. Confira a assinatura no VALIDAR do ITI.')
    def refresh_certs(self):
        from windows_store import list_certificates
        def loaded(items):
            self.certs.clear()
            for item in items:self.certs.addItem(f'{item["name"]}\nCertificado instalado no Windows  •  Validade: {item["expires"]}',item)
            self.report.setPlainText(f'{len(items)} certificado(s) RSA com chave privada e uso de assinatura encontrados no usuário atual.' if items else 'Nenhum certificado RSA elegível. Verifique a instalação no repositório Pessoal do usuário atual ou use PFX.')
        self.run_job(list_certificates,loaded)
    def choose_pfx(self):
        p,_=QFileDialog.getOpenFileName(self,'Certificado A1','','Certificados (*.pfx *.p12)')
        if p:self.pfx.setText(p)
    def open_pdf(self):
        p,_=QFileDialog.getOpenFileName(self,'Abrir PDF','','PDF (*.pdf)')
        if p:self.batch_paths=[];self.load(p)
    def open_batch(self):
        from ui_features import BatchFilesDialog
        dialog=BatchFilesDialog(self,self.batch_paths,self.placements)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.batch_paths=dialog.paths;self.placements=dialog.placements;self.load(self.batch_paths[0])
            self.label.setText(f'{len(self.batch_paths)} PDFs no lote')
            self.audit_desc.setText('Lote preparado. Clique em ASSINAR DOCUMENTO para escolher o método e o signatário.')
    def pick_position(self):
        if not self.path:return
        from ui_features import PositionDialog
        key=str(Path(self.path).resolve())
        try:dialog=PositionDialog(self.path,self,self.placements.get(key),preview_name=self.name.text() or 'NOME DO ASSINANTE',method='cpf' if self.signing_mode()==2 else 'cert')
        except Exception as exc:QMessageBox.warning(self,'Prévia indisponível',str(exc));return
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.placements[key]=dialog.chosen;self.position.setCurrentIndex(1)
            self.report.setPlainText(f'Posição da chancela escolhida na página {dialog.chosen["page_index"]+1}.')
    def update_batch_progress(self,value):
        current,total,name=value
        if self.batch_progress is not None:
            self.batch_progress.setLabelText(f'{current} de {total} PDFs concluídos\n{name}');self.batch_progress.setValue(current)
    def start_batch(self,mode):
        from batch import sign_batch
        from threading import Event
        folder=QFileDialog.getExistingDirectory(self,'Salvar resultados do lote em')
        if not folder:return
        cancel=Event();sources=list(self.batch_paths);positions=dict(self.placements)
        pfx=self.pfx.text();password=self.password.text();self.password.clear();cert=self.certs.currentData()
        name=self.name.text();cpf=self.cpf.text();birth=self.birth.text();visible=self.visible.isChecked()
        self.batch_progress=QProgressDialog('Preparando lote…','Cancelar após o PDF atual',0,len(sources),self)
        self.batch_progress.setWindowModality(Qt.WindowModality.WindowModal);self.batch_progress.setWindowTitle('Assinatura em lote');self.batch_progress.setMinimumDuration(0);self.batch_progress.setAutoClose(False);self.batch_progress.setAutoReset(False);self.batch_progress.canceled.connect(cancel.set)
        def completed(rows):
            successes=[r for r in rows if r['status']=='concluido'];failures=[r for r in rows if r['status']=='erro'];stopped=[r for r in rows if r['status']=='cancelado']
            self.batch_paths=[];self.placements={}
            if successes:self.load(successes[0]['destination']);self.page=len(self.pdf)-1;self.render()
            self.name.clear();self.cpf.clear();self.birth.clear()
            self.status.setText('● Lote concluído')
            self.audit_desc.setText(f'{len(successes)} concluídos • {len(failures)} erros • {len(stopped)} cancelados')
            lines=[f'Pasta: {folder}']
            for r in rows:
                lines.append(Path(r['source']).name+' — '+r['status'])
                if r.get('destination'):lines.append('Salvo: '+Path(r['destination']).name)
                if r.get('error'):lines.append(r['error'])
            self.report.setPlainText('\n\n'.join(lines))
        def operation():
            return sign_batch(sources,folder,method='cpf' if mode==2 else 'cert',pfx_path=pfx,password=password,windows_cert=cert if mode==0 else None,name=name,cpf=cpf,birth=birth,placements=positions,visible=visible,progress=lambda i,n,p:self.job.progress.emit((i,n,p)),cancelled=cancel.is_set)
        self.dialog.hide();self.run_job(operation,completed)
    def load(self,p):
        try:
            new=pdfium.PdfDocument(p)
            new.init_forms()
            if not len(new):raise ValueError('PDF sem páginas.')
            if self.pdf:self.pdf.close()
            self.pdf=new;self.path=p;self.page=0;self.render();self.status.setText('● Aguardando assinatura');self.audit_desc.setText('O documento está pronto para receber uma assinatura. Clique em ASSINAR DOCUMENTO para continuar.');self.report.setPlainText('Clique em Assinaturas para verificar o arquivo.')
        except Exception as e:QMessageBox.warning(self,'Não foi possível abrir',str(e))
    def move(self,step):
        if self.pdf:self.page=max(0,min(len(self.pdf)-1,self.page+step));self.render()
    def render(self):
        page=self.pdf[self.page];bitmap=page.render(scale=min(1.35,max(.5,min(555,self.scroll.viewport().width()-90)/page.get_width())), draw_annots=True);pil=bitmap.to_pil().convert('RGB');data=pil.tobytes();img=QImage(data,pil.width,pil.height,pil.width*3,QImage.Format.Format_RGB888).copy();self.image.setPixmap(QPixmap.fromImage(img));self.label.setText(Path(self.path).name);self.pagination.setText(f'{self.page+1} / {len(self.pdf)}');bitmap.close();page.close()
    def run_job(self,operation,callback):
        if self.job and self.job.isRunning():return
        for b in self.actions+[self.sign,self.choose,self.refresh,self.mode,self.source]:b.setEnabled(False)
        self.report.show();self.report.setPlainText('Processando…')
        self.job=Job(operation)
        self.job.done.connect(callback)
        self.job.failed.connect(lambda message:QMessageBox.warning(self.dialog if self.dialog.isVisible() else self,'Operação não concluída',message))
        self.job.finished.connect(self.finished)
        self.job.progress.connect(self.update_batch_progress)
        self.job.start()
    def finished(self):
        if self.batch_progress is not None:self.batch_progress.close();self.batch_progress=None
        for b in self.actions+[self.sign,self.choose,self.refresh,self.mode,self.source]:b.setEnabled(True)
        if self.report.toPlainText()=='Processando…':self.report.setPlainText('Operação não concluída.')
    def show_report(self,results):
        from html import escape
        self.report.show()
        if not results:
            self.status.setText('● Não assinado');self.detected.setText('✓  ASSINATURAS DETECTADAS ( 0 )')
            self.report.setPlainText('Nenhuma assinatura digital encontrada. Chancelas por CPF não são assinaturas criptográficas.');return
        cards=[]
        for i,r in enumerate(results,1):
            if r.get('error'):
                cards.append(f'<p><b>Assinatura {i}</b><br/>Não foi possível verificar.</p>');continue
            ok=r['intact'] and r['valid'] and r['allowed']
            name=r['signer'].split(';')[0].removeprefix('Common Name: ')
            cards.append(f'<p style="color:#172b45"><b>{escape(name)}</b></p><p style="color:{"#058366" if ok else "#b45533"}">{"Integridade criptográfica OK" if ok else "Verificação requer atenção"}</p><p style="font-size:10px;color:#7c8a9f">Assinatura {i} · Confiança ICP-Brasil não certificada pelo aplicativo<br/>Revogação não consultada</p><hr/>')
        self.report.setHtml(''.join(cards));self.detected.setText(f'✓  ASSINATURAS DETECTADAS ( {len(results)} )')
        ok=all(r.get('intact') and r.get('valid') and r.get('allowed') for r in results)
        self.status.setText('● ÍNTEGRO' if ok else '● Atenção');self.status.setStyleSheet('background:#d8faec;color:#00876d;border-radius:8px;padding:3px 6px;font-size:9px;font-weight:bold');self.audit_desc.setText('A assinatura criptográfica foi conferida. Confiança ICP-Brasil e revogação precisam de validação externa.' if ok else 'Foram encontradas assinaturas que precisam de conferência.')
    def verify(self):
        if self.path:
            path=self.path;self.run_job(lambda:inspect_pdf(path),self.show_report)
    def sign_document(self):
        if not self.path:QMessageBox.warning(self,'Dados necessários','Abra um PDF.');return
        mode=self.signing_mode()
        if mode==0 and self.certs.currentData() is None:QMessageBox.warning(self,'Certificado','Busque e selecione um certificado instalado.');return
        if mode==1 and not self.pfx.text():QMessageBox.warning(self,'Certificado','Selecione seu arquivo PFX.');return
        key=str(Path(self.path).resolve())
        if self.batch_paths:
            self.start_batch(mode);return
        if mode==2 or self.visible.isChecked():
            from ui_features import PositionDialog
            try:dialog=PositionDialog(self.path,self,self.placements.get(key),preview_name=self.name.text() or 'NOME DO ASSINANTE',method='cpf' if mode==2 else 'cert')
            except Exception as exc:QMessageBox.warning(self,'PDF não disponível',str(exc));return
            if dialog.exec()!=QDialog.DialogCode.Accepted:return
            self.placements[key]=dialog.chosen
        chosen=self.placements.get(key,{})
        box=chosen.get('box');page=chosen.get('page_index');repeat_options={k:chosen[k] for k in ('pages','rubrics') if k in chosen}
        suffix='_declarado.pdf' if mode==2 else '_assinado.pdf'
        out,_=QFileDialog.getSaveFileName(self,'Salvar cópia',str(Path(self.output_source() if hasattr(self,'output_source') else self.path).with_name(Path(self.output_source() if hasattr(self,'output_source') else self.path).stem+suffix)),'PDF (*.pdf)')
        if not out:return
        if not out.lower().endswith('.pdf'):out+='.pdf'
        source=self.path;pfx=self.pfx.text();password=self.password.text();reason=self.reason.text();self.password.clear()
        name=self.name.text();cpf=self.cpf.text();birth=self.birth.text();consent=True
        cert=self.certs.currentData();visible=self.visible.isChecked()
        def completed(results):
            self.placements.pop(str(Path(source).resolve()),None)
            self.load(out)
            self.page=page if page is not None else len(self.pdf)-1;self.render();self.report.show()
            if mode==2:
                self.name.clear();self.cpf.clear();self.birth.clear()
                self.status.setText('● CPF registrado');self.audit_desc.setText('CPF declarado. Selo técnico local de integridade; identidade não autenticada.')
                self.report.setPlainText('Chancela eletrônica criada nas páginas e posições escolhidas. Dados declarados; identidade não autenticada. Selo técnico local autoassinado protege a integridade do PDF. Não ICP-Brasil.')
            else:self.show_report(results)
            QMessageBox.information(self,'Cópia salva','Confira as páginas selecionadas e, para assinatura com certificado, valide também no ITI.')
        if mode==2:
            from cpf_protected import make_protected_declaration as make_declaration
            operation=lambda:make_declaration(source,out,name,cpf,birth,consent,page_index=page,box=box,**repeat_options)
        else:operation=lambda:sign_pdf(source,out,pfx,password,reason,windows_cert=cert if mode==0 else None,visible=visible,page_index=page,box=box,**repeat_options)
        self.dialog.hide()
        self.run_job(operation,completed)
    def closeEvent(self,event):
        if self.job and self.job.isRunning():QMessageBox.information(self,'Processando','Aguarde a operação terminar.');event.ignore();return
        if self.pdf:self.pdf.close()
        event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv)
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Conecta.AssinadorConecta')
    app.setWindowIcon(QIcon(str(Path(__file__).parent/'assets'/'app_icon.ico')))
    window=Window();window.show();sys.exit(app.exec())
