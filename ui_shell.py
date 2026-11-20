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
    apply_light_palette()
    w.dialog.setObjectName('signatureDialog')
    old=w.takeCentralWidget();root=QWidget();root.setObjectName('surface');w.setCentralWidget(root)
    close_path=(Path(__file__).parent/'assets/close.svg').as_posix();w.setStyleSheet(STYLE.replace('__CLOSE__',close_path)+"QPushButton#tab{font-size:13px;padding:20px 12px;background:#edf4ff;border:1px solid #d5e5fc} QPushButton#tab:checked{background:#dcecff;border:1px solid #1673f5} QPushButton#nav:checked{border-left:0;border-bottom:3px solid #0867ff}")
    w.actions=[];outer=QVBoxLayout(root);outer.setContentsMargins(18,12,18,10);outer.setSpacing(10)
    masthead = QFrame()
    masthead.setStyleSheet('QFrame {background: white; border: none;}')
    header = QHBoxLayout(masthead)
    header.setContentsMargins(12, 5, 8, 5)
    header.setSpacing(12)
    logo = QPixmap(str(Path(__file__).parent / 'assets/logo-conecta-pdf.png'))
    for bounds in [(26, 28, 140, 152), (172, 55, 438, 68)]:
        part = QLabel()
        section = logo.copy(*bounds)
        part.setPixmap(section.scaledToHeight(47 if bounds[0] == 26 else 22, Qt.TransformationMode.SmoothTransformation))
        header.addWidget(part)
    header.addSpacing(25)
    for name,label,fn in [('home','Início',w.home),('file','Documentos',w.open_pdf),('clock','Recentes',w.recent),('settings','Configurações',w.preferences)]:
        b=w.button(header,label,fn,'nav');b.setIcon(icon(name));b.setIconSize(QSize(21,21));b.setCheckable(True);b.setAutoExclusive(True);b.setChecked(name=='home')
    header.addStretch();w.launch=w.button(header,'Assinar',w.open_signing,'primary');w.launch.setIcon(icon('pen','white'));w.launch.setIconSize(QSize(23,23));w.launch.setMinimumWidth(135);outer.addWidget(masthead)
    w.tabs=QTabBar();w.tabs.setExpanding(False);w.tabs.setTabsClosable(True);w.tabs.setElideMode(Qt.TextElideMode.ElideMiddle);w.tabs.setUsesScrollButtons(True);w.tabs.currentChanged.connect(w.switch_tab);w.tabs.tabCloseRequested.connect(w.close_tab);outer.addWidget(w.tabs)
    strip = QFrame()
    strip.setStyleSheet("QFrame {background: white;} QToolButton {background: transparent; border: none; border-radius: 7px;} QToolButton:hover, QToolButton:focus {background: #e6f0ff;} QToolButton:pressed {background: #ccdef8;}")
    toolbar = QHBoxLayout(strip)
    toolbar.setContentsMargins(10, 5, 10, 5)
    toolbar.setSpacing(3)

    def action(symbol, label, callback):
        button = QToolButton()
        button.setIcon(icon(symbol))
        button.setIconSize(QSize(22, 22))
        button.setText({'Abrir documento':'Abrir','Salvar PDF':'Salvar','Girar visualização':'Girar','Mostrar páginas':'Páginas','Documento para PDF':'Converter','Exportar PDF para texto ou imagens':'Exportar','Assinar em lote':'Lote','Imagens para PDF':'Imagens'}.get(label,label))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setMinimumSize(64, 62)
        if symbol in ('left','right'):
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setMinimumSize(32,32)
            button.setFixedSize(32,32)
        button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        button.setToolTip(label)
        button.setAccessibleName(label)
        button.clicked.connect(callback)
        toolbar.addWidget(button)
        w.actions.append(button)

    groups = [
        [('folder','Abrir documento',w.open_pdf), ('save','Salvar PDF',w.save_pdf), ('print','Imprimir',w.print_pdf)],
        [('merge','Juntar PDFs',w.merge_pdfs), ('split','Separar PDF',w.split_pdf), ('image','Imagens para PDF',w.convert_images), ('scan','Digitalizar',w.scan_document)],
        [('file','Documento para PDF',lambda: convert(w)), ('save','Exportar PDF para texto ou imagens',lambda: convert(w, True))],
        [('pen','Assinar em lote',w.open_batch), ('search','Pesquisar',w.toggle_search), ('rotate','Girar visualização',w.rotate), ('pages','Mostrar páginas',lambda: w.thumbs.setVisible(not w.thumbs.isVisible())), ('info','Detalhes',w.show_details)],
    ]
    for group in groups:
        for entry in group:
            action(*entry)
        if group is not groups[-1]:
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.VLine)
            toolbar.addWidget(divider)
        toolbar.addSpacing(4)
    tool_scroll = QScrollArea()
    tool_scroll.setWidgetResizable(True)
    tool_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    tool_scroll.setWidget(strip)
    tool_scroll.setFixedHeight(86)
    outer.addWidget(tool_scroll)
    navigation = QFrame()
    navigation.setStyleSheet('QToolButton {background:transparent;border:0;border-radius:6px;padding:6px} QToolButton:hover {background:#e6f0ff}')
    toolbar = QHBoxLayout(navigation)
    toolbar.setContentsMargins(4,0,4,0)
    caption = QLabel('ÁREA DO DOCUMENTO')
    caption.setObjectName('muted')
    toolbar.addWidget(caption)
    toolbar.addStretch()
    w.zoom = QComboBox()
    w.zoom.addItems(['Página inteira','Ajustar largura','75%','100%','125%','150%','200%'])
    w.zoom.currentTextChanged.connect(w.change_zoom)
    toolbar.addWidget(w.zoom)
    action('left','Página anterior',lambda: w.move(-1))
    w.pagination = QLabel('0 / 0')
    toolbar.addWidget(w.pagination)
    action('right','Próxima página',lambda: w.move(1))
    outer.addWidget(navigation)
    w.search_bar=QWidget();search=QHBoxLayout(w.search_bar);search.setContentsMargins(0,0,0,0);w.query=QLineEdit();w.query.setPlaceholderText('Pesquisar no documento…');w.query.returnPressed.connect(w.find_text);search.addWidget(w.query);w.button(search,'Localizar',w.find_text);w.button(search,'Fechar',w.search_bar.hide);w.search_bar.hide();outer.addWidget(w.search_bar)
    view=QHBoxLayout();view.setSpacing(1);w.thumbs=QListWidget();w.thumbs.setFixedWidth(148);w.thumbs.setIconSize(QSize(96,130));w.thumbs.setViewMode(QListView.ViewMode.IconMode);w.thumbs.setFlow(QListView.Flow.TopToBottom);w.thumbs.setWrapping(False);w.thumbs.setResizeMode(QListView.ResizeMode.Adjust);w.thumbs.setMovement(QListView.Movement.Static);w.thumbs.setGridSize(QSize(140,166));w.thumbs.currentRowChanged.connect(w.thumbnail_selected);view.addWidget(w.thumbs)
    w.scroll=QScrollArea();w.scroll.setWidgetResizable(True);w.image=QLabel();w.image.setAlignment(Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop);w.image.setStyleSheet('background:#e9eef5;padding:12px;color:#617590;font-size:18px');w.scroll.setWidget(w.image);view.addWidget(w.scroll,1)
    panel = QFrame(); panel.setObjectName('card'); panel.setFixedWidth(278)
    side = QVBoxLayout(panel); side.setContentsMargins(18,22,18,20); side.setSpacing(16)
    heading = QLabel('Assinar documento'); heading.setObjectName('heading'); side.addWidget(heading)
    hint = QLabel('Escolha o método de assinatura.'); hint.setObjectName('muted'); hint.setWordWrap(True); side.addWidget(hint)
    methods = QHBoxLayout(); methods.setSpacing(8)
    for label, symbol, method in [('Certificado','cert',0),('CPF','user',1)]:
        b = w.button(methods,label,lambda checked=False,m=method:w.open_method(m),'secondary')
        b.setIcon(icon(symbol,'#075be8')); b.setToolTip('Assinar com '+label)
    side.addLayout(methods)
    description = QLabel('Posicione sua chancela na etapa de assinatura. Você pode ajustar a página e o local antes de confirmar.'); description.setWordWrap(True); description.setObjectName('muted'); side.addWidget(description)
    side.addStretch()
    verify = w.button(side,'Verificar assinaturas',w.verify); verify.setIcon(icon('cert'))
    info = w.button(side,'Detalhes do documento',w.show_details); info.setIcon(icon('info'))
    view.addWidget(panel); outer.addLayout(view,1)
    w.label=QLabel('Documentos processados no seu computador');w.label.setObjectName('muted');outer.addWidget(w.label)
    w.details_dialog=QDialog(w);w.details_dialog.setWindowTitle('Detalhes do documento');w.details_dialog.resize(650,480);d=QVBoxLayout(w.details_dialog)
    w.audit_desc=QLabel('Abra um PDF ou XML de NF-e modelo 55.');w.audit_desc.setWordWrap(True);d.addWidget(w.audit_desc)
    w.status=QLabel('Assinatura: não verificada');w.status.setWordWrap(True);d.addWidget(w.status)
    w.detected=QLabel('Assinaturas');d.addWidget(w.detected);w.report=QTextEdit();w.report.setReadOnly(True);d.addWidget(w.report,1);w.button(d,'Verificar assinaturas',w.verify);w.button(d,'Conferir no VALIDAR ITI ↗',lambda:w.open_url('https://validar.iti.gov.br/'))
    old.deleteLater();return root
