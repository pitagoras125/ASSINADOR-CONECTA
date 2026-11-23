"""Interface nativa baseada na composição visual aprovada."""
from pathlib import Path
from conversion_ui import convert
from PySide6.QtCore import Qt,QSize,QByteArray,QRectF
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QPalette
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication,QWidget,QFrame,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QTabBar,QComboBox,QLineEdit,QScrollArea,QListWidget,QTextEdit,QDialog,QMenu,QToolButton,QListView,QSizePolicy)

PATHS={
'merge':'<path d="M3 4v4l8 6v6m10-16v4l-10 6m-4 2 4 4 4-4"/>',
'split':'<path d="M12 21v-7L4 6m0 5V5h6m2 9 8-8m-6-1h6v6"/>',
'image':'<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m4 17 5-5 3 3 4-6 5 7"/>',
'scan':'<path d="m4 10 14-7 2 2-14 7M3 14h18v6H3zM16 17h2"/>',
'rotate':'<path d="M4 11a8 8 0 1 1 2 8M4 4v7h7"/>',
'pages':'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
'home':'<path d="m3 10 9-7 9 7v10H5V10m4 10v-7h6v7"/>',
'file':'<path d="M6 3h8l5 5v13H6zM14 3v6h5"/>',
'folder':'<path d="M3 6h7l2 3h9v11H3z"/>',
'clock':'<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
'settings':'<path d="m9 3 6 0 1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1z"/><circle cx="12" cy="12" r="3"/>',
'save':'<path d="M4 3h14l3 3v15H3V3zm3 0v7h10V3M7 21v-7h10v7"/>',
'print':'<path d="M7 8V3h10v5M7 17H3V9h18v8h-4M7 14h10v7H7z"/><path d="M17 11h1"/>',
'cert':'<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 9h18M7 13h4v4H7zM14 13h4m-4 3h4"/>',
'user':'<circle cx="12" cy="7" r="4"/><path d="M4 21v-3c0-7 16-7 16 0v3z"/>',
'cursor':'<path d="M5 3v17l5-5 4 7 3-2-4-7h7z"/>',
'pen':'<path d="m6 14 10-11 5 5-11 10-7 3zM6 14l4 4M3 21l5-5M14 5l5 5"/>',
'search':'<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6M7 10h6m-3-3v6"/>',
'left':'<path d="m15 5-7 7 7 7"/>','right':'<path d="m9 5 7 7-7 7"/>',
'more':'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
'info':'<circle cx="12" cy="12" r="9"/><path d="M12 11v7m0-12v2"/>'}

def icon(name,color='#132b51',size=24):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'
    pix=QPixmap(size*2,size*2);pix.fill(Qt.GlobalColor.transparent);pix.setDevicePixelRatio(2)
    painter=QPainter(pix);QSvgRenderer(QByteArray(svg.encode())).render(painter,QRectF(0,0,size,size));painter.end();return QIcon(pix)

STYLE='''
QWidget{font-family:"Segoe UI";font-size:14px;color:#142849;background:transparent}
QMainWindow,QWidget#surface{background:#f4f7fc}
QDialog,QMessageBox,QProgressDialog,QFileDialog{background-color:#ffffff;color:#142849}
QMessageBox QLabel,QDialog QLabel{color:#142849;background:transparent}
QDialog QLineEdit,QDialog QTextEdit,QDialog QListWidget{background-color:#ffffff;color:#142849;selection-background-color:#dcecff;selection-color:#142849}
QDialog QDialogButtonBox{background:transparent}
QDialog#signatureDialog{background:transparent}
QFrame#rail{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #edf5ff,stop:1 #f7faff)}
QFrame#card{background:white;border:1px solid #e5edf7;border-radius:13px}
QLabel#heading{font-size:20px;font-weight:700;color:#0a2046} QLabel#muted{color:#536989;font-size:13px}
QPushButton{background:white;border:1px solid #dce7f6;border-radius:7px;padding:9px 12px;text-align:left}
QPushButton:focus{border:2px solid #075be8} QPushButton:hover{background:#eaf3ff;border-color:#a4c9ff} QPushButton:disabled{color:#92a3bb;background:#eff3f8}
QPushButton#nav{background:transparent;border:0;padding:14px 16px;font-size:15px;border-radius:7px}
QPushButton#nav:checked{background:#e3f0ff;color:#005cef;border-left:3px solid #0867ff}
QPushButton#primary{background:#075ff0;color:white;border:0;padding:15px 13px;font-size:13px;font-weight:600}
QPushButton#primary:hover{background:#0051cc} QPushButton#secondary{background:#eaf3ff;color:#073d9a;border:0;padding:15px 13px;font-size:14px;font-weight:600}
QPushButton#position{border:0;padding:10px 0;background:transparent;color:#25456f}
QPushButton#details{background:white;border:1px solid #4088ff;color:#0058da;text-align:center;font-weight:600;padding:12px}
QPushButton#icon{border:0;background:transparent;padding:7px}
QComboBox,QLineEdit{background:white;border:1px solid #dbe6f6;border-radius:6px;padding:7px 10px}
QComboBox::drop-down{border:0;width:20px} QComboBox::down-arrow{image:none;border-top:5px solid #365378;border-left:4px solid transparent;border-right:4px solid transparent;width:0;height:0}
QTabBar::tab{background:transparent;border:1px solid transparent;padding:13px 18px;margin-right:3px;min-width:130px;max-width:270px}
QTabBar::tab:selected{background:white;border:1px solid #dce8f8;border-top:2px solid #1375ff;border-top-left-radius:9px;border-top-right-radius:9px;color:#004cbd}
QTabBar::close-button{image:url(__CLOSE__);width:14px;height:14px}
QScrollArea{border:0;background:#e9eef5} QListWidget{background:#e8f0f9;border:0;outline:0}
QListWidget::item{padding:7px;margin:6px;border:1px solid transparent;border-radius:3px}
QListWidget::item:selected{background:#f4f9ff;border:2px solid #2477ff;color:#0055d8}
QScrollBar:vertical{background:#eef3f8;width:9px} QScrollBar::handle:vertical{background:#c6d3e2;min-height:35px;border-radius:4px}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}
QTextEdit{background:white;border:1px solid #dfE8f5;border-radius:8px;padding:12px}
QMenu{background:white;border:1px solid #dce7f6;padding:6px} QMenu::item{padding:9px 20px} QMenu::item:selected{background:#e8f2ff}
'''

def apply_light_palette():
    # Explicit palette covers dialogs whose native platform palette is dark.
    palette=QPalette()
    roles={QPalette.ColorRole.Window:'#ffffff',QPalette.ColorRole.WindowText:'#142849',
           QPalette.ColorRole.Base:'#ffffff',QPalette.ColorRole.AlternateBase:'#f2f6fc',
           QPalette.ColorRole.Text:'#142849',QPalette.ColorRole.Button:'#ffffff',
           QPalette.ColorRole.ButtonText:'#142849',QPalette.ColorRole.ToolTipBase:'#ffffff',
           QPalette.ColorRole.ToolTipText:'#142849',QPalette.ColorRole.Highlight:'#dcecff',
           QPalette.ColorRole.HighlightedText:'#142849',QPalette.ColorRole.PlaceholderText:'#64758c',
           QPalette.ColorRole.Link:'#0867ff'}
    for group in (QPalette.ColorGroup.Active,QPalette.ColorGroup.Inactive,QPalette.ColorGroup.Disabled):
        for role,color in roles.items():palette.setColor(group,role,QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Text,QColor('#8797ad'))
    palette.setColor(QPalette.ColorGroup.Disabled,QPalette.ColorRole.ButtonText,QColor('#8797ad'))
    QApplication.instance().setPalette(palette)

def build_shell(w):
    from inline_preview import DocumentPreview
    apply_light_palette()
    old=w.takeCentralWidget();root=QWidget();root.setObjectName('surface');w.setCentralWidget(root)
    close_path=(Path(__file__).parent/'assets/close.svg').as_posix()
    w.setStyleSheet(STYLE.replace('__CLOSE__',close_path)+"""
QWidget{font-size:13px} QFrame#masthead{background:#102344}
QFrame#masthead QLabel{color:white;font-size:19px;font-weight:700}
QTabBar::tab{background:#344865;color:#e8eef9;padding:10px 16px;margin:3px 3px 0 0;min-width:120px;max-width:240px;border:0;border-top-left-radius:8px;border-top-right-radius:8px}
QTabBar::tab:selected{background:#f6f8fc;color:#0054de;border:0}
QPushButton#headerAction{color:white;background:transparent;border:0;padding:7px}
QFrame#card{border-radius:0;border:0;border-left:1px solid #d5dfed;background:white}
QPushButton#tab{padding:9px 8px;border:1px solid #ccd7e7;border-radius:5px;background:white;text-align:center}
QPushButton#tab:checked{background:#dceaff;color:#0055e8;border-color:#1467ff;font-weight:600}
QPushButton#primary{padding:11px;font-size:14px;text-align:center}
QLabel#heading{font-size:19px} QListWidget{background:#f8faff}
QCheckBox{spacing:7px} QSpinBox{background:white;border:1px solid #dbe6f6;padding:6px;border-radius:5px}
QSlider::groove:horizontal{height:5px;background:#d4dce6;border-radius:2px} QSlider::sub-page:horizontal{background:#0872ff} QSlider::handle:horizontal{background:white;border:1px solid #0872ff;width:16px;margin:-6px 0;border-radius:8px}
""")
    w.actions=[];outer=QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
    masthead=QFrame();masthead.setObjectName('masthead');header=QHBoxLayout(masthead);header.setContentsMargins(20,9,16,9);header.setSpacing(10)
    logo=QLabel();logo.setPixmap(QPixmap(str(Path(__file__).parent/'assets/app_icon.png')).scaled(32,32,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));header.addWidget(logo)
    header.addWidget(QLabel('Conecta PDF'));header.addSpacing(14)
    w.tabs=QTabBar();w.tabs.setExpanding(False);w.tabs.setTabsClosable(True);w.tabs.setElideMode(Qt.TextElideMode.ElideMiddle);w.tabs.setUsesScrollButtons(True);w.tabs.currentChanged.connect(w.switch_tab);w.tabs.tabCloseRequested.connect(w.close_tab);header.addWidget(w.tabs,1)
    w.button(header,'+',w.open_pdf,'headerAction').setToolTip('Abrir documento em uma nova aba')
    w.button(header,'Recentes',w.recent,'headerAction')
    w.button(header,'Configurações',w.preferences,'headerAction').setIcon(icon('settings','white',18));outer.addWidget(masthead)
    w.launch=w.button(header,'Assinar',w.open_signing,'primary')
    w.launch.setIcon(icon('pen','white'))
    w.launch.setMinimumWidth(112)
    w.search_bar=QWidget();search=QHBoxLayout(w.search_bar);w.query=QLineEdit();w.query.setPlaceholderText('Pesquisar no documento…');w.query.returnPressed.connect(w.find_text);search.addWidget(w.query);w.button(search,'Localizar',w.find_text);w.button(search,'Fechar',w.search_bar.hide);w.search_bar.hide();outer.addWidget(w.search_bar)
    view=QHBoxLayout();view.setSpacing(0);view.setContentsMargins(0,0,0,0)
    rail=QFrame()
    rail.setObjectName('commandRail')
    rail.setFixedWidth(178)
    rail.setStyleSheet('QFrame#commandRail{background:#f1f5fa;border-right:1px solid #dae3ed} QLabel{font-size:12px;font-weight:600;color:#55677b} QPushButton{background:transparent;color:#182e47;border:1px solid transparent;border-radius:7px;padding:5px 9px;text-align:left} QPushButton:hover{background:#dce9f6} QPushButton:focus{border:1px solid #0067b8}')
    nav=QVBoxLayout(rail)
    nav.setContentsMargins(12,10,12,10)
    nav.setSpacing(2)
    groups=[
        ('Arquivo',[('folder','Abrir',w.open_pdf),('save','Salvar',w.save_pdf),('print','Imprimir',w.print_pdf)]),
        ('Ferramentas',[('merge','Juntar PDFs',w.merge_pdfs),('split','Separar PDF',w.split_pdf),('image','Imagens para PDF',w.convert_images),('file','Converter',lambda:convert(w)),('save','Exportar',lambda:convert(w,True)),('scan','Digitalizar',w.scan_document),('pen','Assinar em lote',w.open_batch)]),
        ('Visualização',[('rotate','Girar',w.rotate),('search','Pesquisar',w.toggle_search),('pages','Páginas',lambda:w.pages_panel.setVisible(not w.pages_panel.isVisible())),('info','Detalhes',w.show_details)])]
    for title,commands in groups:
        nav.addSpacing(5)
        nav.addWidget(QLabel(title))
        for symbol,label,callback in commands:
            button=QPushButton(label)
            button.setIcon(icon(symbol,'#315875'))
            button.setIconSize(QSize(18,18))
            button.clicked.connect(callback)
            button.setToolTip(label)
            nav.addWidget(button)
            w.actions.append(button)
    nav.addStretch()
    rail_scroll=QScrollArea()
    rail_scroll.setWidgetResizable(True)
    rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    rail_scroll.setFixedWidth(188)
    rail_scroll.setWidget(rail)
    view.addWidget(rail_scroll)
    w.pages_panel=QWidget();w.pages_panel.setFixedWidth(166);pages=QVBoxLayout(w.pages_panel);pages.setContentsMargins(8,14,8,0);title=QLabel('Páginas');title.setObjectName('heading');pages.addWidget(title)
    w.thumbs=QListWidget();w.thumbs.setIconSize(QSize(112,150));w.thumbs.setViewMode(QListView.ViewMode.IconMode);w.thumbs.setFlow(QListView.Flow.TopToBottom);w.thumbs.setWrapping(False);w.thumbs.setResizeMode(QListView.ResizeMode.Adjust);w.thumbs.setMovement(QListView.Movement.Static);w.thumbs.setGridSize(QSize(142,184));w.thumbs.currentRowChanged.connect(w.thumbnail_selected);pages.addWidget(w.thumbs);view.addWidget(w.pages_panel)
    w.scroll=QScrollArea();w.scroll.setWidgetResizable(True);w.image=DocumentPreview(w);w.image.setAlignment(Qt.AlignmentFlag.AlignCenter);w.image.setStyleSheet('background:#e4eaf3;color:#617590;font-size:17px');w.scroll.setWidget(w.image)
    from PySide6.QtWidgets import QStackedWidget
    w.workspace=QStackedWidget()
    welcome=QWidget()
    welcome.setStyleSheet('QWidget#welcomeCard{background:white;border:1px solid #dbe3ee;border-radius:16px}')
    center=QVBoxLayout(welcome)
    card=QFrame()
    card.setObjectName('welcomeCard')
    card.setFixedWidth(420)
    body=QVBoxLayout(card)
    body.setContentsMargins(34,32,34,32)
    body.setSpacing(14)
    emblem=QLabel()
    emblem.setPixmap(icon('folder','#0067b8',42).pixmap(42,42))
    body.addWidget(emblem)
    title=QLabel('Abrir documento')
    title.setStyleSheet('font-size:26px;font-weight:600;color:#142b46')
    body.addWidget(title)
    body.addWidget(QLabel('Arraste um PDF ou um XML de NF-e para esta janela.'))
    w.button(body,'Escolher arquivo',w.open_pdf,'primary')
    center.addWidget(card,0,Qt.AlignmentFlag.AlignCenter)
    w.workspace.addWidget(welcome)
    w.workspace.addWidget(w.scroll)
    view.addWidget(w.workspace,1)
    outer.addLayout(view,1)
    w.signature_panel=w.launch
    w.method_picker=QDialog(w)
    w.method_picker.setWindowTitle('Assinar documento')
    pick_layout=QVBoxLayout(w.method_picker)
    pick_layout.setContentsMargins(24,22,24,24)
    pick_layout.setSpacing(16)
    pick_title=QLabel('Como deseja assinar?')
    pick_title.setObjectName('heading')
    pick_layout.addWidget(pick_title)
    picker=QHBoxLayout()
    pick_layout.addLayout(picker)
    picker.setContentsMargins(0,0,0,0)
    for button,label in [(w.cert_choice,'Certificado digital'),(w.cpf_choice,'CPF')]:
        button.setText(label)
        button.setIcon(icon('cert' if button is w.cert_choice else 'user','#0067b8',26))
        button.setIconSize(QSize(26,26))
        button.setMinimumSize(175,68)
        picker.addWidget(button)
    w.dialog=QDialog(w)
    w.dialog.setWindowTitle('Assinar documento')
    w.dialog.setModal(True)
    layout=QVBoxLayout(w.dialog)
    layout.setContentsMargins(24,20,24,20)
    w.cert_heading.setText('Certificados instalados')
    w.refresh.setText('Atualizar lista')
    w.certs.setWordWrap(True)
    w.certs.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    w.certs.setMinimumHeight(160)
    w.certs.setStyleSheet('QListWidget{background:#f7f8fa;border:1px solid #dae0e7;border-radius:8px;padding:4px} QListWidget::item{background:white;border:1px solid #e3e7ed;border-radius:6px;padding:8px;color:#202124} QListWidget::item:selected{background:#e5f1fb;color:#00395e;border:1px solid #0078d4}')
    w.signer_heading=QLabel()
    w.signer_heading.setObjectName('heading')
    layout.addWidget(w.signer_heading)
    w.form.layout().setContentsMargins(0,8,0,6)
    layout.addWidget(w.form)
    actions=QHBoxLayout()
    actions.addStretch()
    cancel=QPushButton('Cancelar')
    cancel.clicked.connect(w.dialog.reject)
    actions.addWidget(cancel)
    actions.addWidget(w.sign)
    layout.addLayout(actions)
    for dialog in (w.method_picker,w.dialog):
        dialog.setStyleSheet('QDialog{background:#f7f8fa} QPushButton{font-family:"Segoe UI";border-radius:6px;padding:7px 12px} QPushButton#primary{background:#0067b8;color:white}')
    footer=QFrame();footer.setStyleSheet('QFrame{background:#f9fbff;border-top:1px solid #d7e0ed}');bottom=QHBoxLayout(footer);bottom.setContentsMargins(14,5,14,5)
    w.label=QLabel('Processamento local');w.label.setObjectName('muted');bottom.addWidget(w.label,1)
    w.button(bottom,'‹',lambda:w.move(-1),'icon');w.pagination=QLabel('0 / 0');bottom.addWidget(w.pagination);w.button(bottom,'›',lambda:w.move(1),'icon')
    w.zoom=QComboBox();w.zoom.addItems(['Página inteira','Ajustar largura','75%','100%','125%','150%','200%']);w.zoom.currentTextChanged.connect(w.change_zoom);bottom.addWidget(w.zoom);bottom.addStretch()
    credit=QLabel('DESENVOLVIDO POR AVANTE SISTEMAS LTDA\nCNPJ 54.713.453/0001-94');credit.setStyleSheet('font-size:9px;font-weight:600');credit.setAlignment(Qt.AlignmentFlag.AlignRight);bottom.addWidget(credit);outer.addWidget(footer)
    w.details_dialog=QDialog(w);w.details_dialog.setWindowTitle('Detalhes do documento');w.details_dialog.resize(650,480);d=QVBoxLayout(w.details_dialog)
    w.audit_desc=QLabel('Abra um PDF ou XML de NF-e modelo 55.');w.audit_desc.setWordWrap(True);d.addWidget(w.audit_desc);w.status=QLabel('Assinatura: não verificada');w.status.setWordWrap(True);d.addWidget(w.status);w.detected=QLabel('Assinaturas');d.addWidget(w.detected);w.report=QTextEdit();w.report.setReadOnly(True);d.addWidget(w.report,1);w.button(d,'Verificar assinaturas',w.verify);w.button(d,'Conferir no VALIDAR ITI ↗',lambda:w.open_url('https://validar.iti.gov.br/'))
    w.inline_signing=True;w.visible.toggled.connect(w.image.update);w.name.textChanged.connect(w.image.invalidate_seal);w.mode.currentIndexChanged.connect(w.image.invalidate_seal)
    w.update_mode();w.form.show();w.sign.show();w.signature_panel.setEnabled(False)
    old.deleteLater();return root
