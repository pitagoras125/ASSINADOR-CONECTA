"""Digitalização local através do driver WIA instalado no Windows."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QVBoxLayout,
)
from reportlab.pdfgen.canvas import Canvas


class ScannerDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Digitalizar documentos')
        self.setMinimumWidth(490)
        self.folder = TemporaryDirectory(prefix='conecta-scan-')
        self.pages = []
        self.target = None
        self.sequence = 1
        self.count = 0
        self.saved = []
        self.pending = None
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)
        self.device = QComboBox()
        row = QHBoxLayout()
        row.addWidget(self.device, 1)
        self.refresh = QPushButton('Buscar scanners')
        row.addWidget(self.refresh)
        form.addRow('Scanner ou multifuncional', row)
        self.quality = QComboBox()
        for name, dpi in [('Padrão do scanner', 0), ('150 dpi', 150), ('300 dpi', 300), ('600 dpi', 600)]:
            self.quality.addItem(name, dpi)
        form.addRow('Resolução', self.quality)
        self.format = QComboBox()
        self.format.addItems(['PDF', 'Imagem PNG', 'Imagem JPEG'])
        form.addRow('Salvar como', self.format)
        self.multiple = QCheckBox('Digitalizar mais de uma página')
        form.addRow(self.multiple)
        self.group = QComboBox()
        self.group.addItems(['Todas as páginas em um único PDF', 'Um PDF por documento'])
        form.addRow('Organização do PDF', self.group)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.scan = QPushButton('Digitalizar')
        self.scan.setObjectName('primary')
        self.next_doc = QPushButton('Concluir documento e iniciar outro')
        self.finish = QPushButton('Concluir e salvar')
        for btn in [self.scan, self.next_doc, self.finish]:
            layout.addWidget(btn)
        self.proc = QProcess(self)
        self.proc.finished.connect(self.completed)
        self.proc.errorOccurred.connect(self.process_error)
        self.scan.clicked.connect(self.capture)
        self.next_doc.clicked.connect(self.document_boundary)
        self.finish.clicked.connect(self.finish_batch)
        self.refresh.clicked.connect(self.discover)
        self.format.currentIndexChanged.connect(self.controls)
        self.multiple.toggled.connect(self.controls)
        self.discover()

    def controls(self):
        idle = self.pending is None
        setup = self.target is None
        for field in [self.device, self.refresh, self.quality, self.format, self.multiple]:
            field.setEnabled(idle and setup)
        pdf = self.format.currentIndex() == 0
        self.group.setEnabled(idle and setup and pdf and self.multiple.isChecked())
        self.scan.setEnabled(idle and self.device.count() > 0 and not (not pdf and self.pages))
        self.scan.setText('Digitalizar próxima página' if self.count else 'Digitalizar')
        self.next_doc.setVisible(bool(self.count and pdf and self.multiple.isChecked() and self.group.currentIndex()))
        self.next_doc.setEnabled(idle and bool(self.pages))
        self.finish.setVisible(bool(self.count))
        self.finish.setEnabled(idle)

    def run(self, action, *args):
        self.pending = action
        self.controls()
        self.status.setText('Buscando scanners…' if action == 'list' else 'Digitalização em andamento…')
        script = Path(__file__).parent / 'assets' / 'windows_scanner.ps1'
        exe = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        self.proc.start(str(exe), ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                   '-File', str(script), action, *args])

    def discover(self):
        self.device.clear()
        self.run('list')

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.pending = None
            self.status.setText('Não foi possível iniciar a busca pelo Windows PowerShell.')
            self.controls()

    def capture(self):
        if self.target is None:
            suffix = ['pdf', 'png', 'jpg'][self.format.currentIndex()]
            name, _ = QFileDialog.getSaveFileName(self, 'Destino da digitalização',
                                                   'Digitalização.' + suffix, f'Arquivo (*.{suffix})')
            if not name:
                return
            self.target = Path(name if name.lower().endswith('.' + suffix) else name + '.' + suffix)
        extension = 'png' if self.device.currentData().startswith('naps/') else 'bmp'
        self.raw = Path(self.folder.name) / f'pagina-{self.count + 1}.{extension}'
        self.raw.unlink(missing_ok=True)
        self.run('scan', self.device.currentData(), str(self.quality.currentData()), str(self.raw))

    def completed(self, code, _status):
        action = self.pending
        self.pending = None
        output = bytes(self.proc.readAllStandardOutput()).decode('utf-8-sig', 'replace').strip()
        error = bytes(self.proc.readAllStandardError()).decode('utf-8', 'replace').strip()
        try:
            if code:
                raise ValueError(error or 'O scanner não concluiu a operação.')
            if action == 'list':
                result = json.loads(output)
                for entry in result['devices']:
                    self.device.addItem(entry['name'], entry['id'])
                self.status.setText('Escolha as opções antes de digitalizar.' if self.device.count() else
                                    'Nenhum scanner encontrado. ' + result['detail'])
            elif action == 'scan':
                with Image.open(self.raw) as page:
                    actual_dpi = (page.info.get('dpi') or (300, 300))[0]
                    page.verify()
                self.pages.append((self.raw, max(1, int(output) or round(actual_dpi) or 300)))
                self.count += 1
                if self.format.currentIndex() or not self.multiple.isChecked():
                    self.save_document()
                if not self.multiple.isChecked():
                    self.success()
                    return
                self.status.setText(f'{self.count} página(s) digitalizada(s). Coloque a próxima folha ou conclua.')
        except Exception as exc:
            if not self.count:
                self.target = None
            self.status.setText(str(exc))
        self.controls()

    def save_document(self):
        if not self.pages:
            return
        dest = self.target
        if self.sequence > 1:
            dest = dest.with_name(f'{dest.stem}-{self.sequence:03d}{dest.suffix}')
        # Reserve new names exclusively; never overwrite an existing document.
        while dest.exists():
            self.sequence += 1
            dest = self.target.with_name(f'{self.target.stem}-{self.sequence:03d}{self.target.suffix}')
        with dest.open('xb') as stream:
            try:
                if self.format.currentIndex() == 0:
                    pdf = Canvas(stream)
                    for path, dpi in self.pages:
                        with Image.open(path) as im:
                            width, height = (n * 72 / dpi for n in im.size)
                        pdf.setPageSize((width, height))
                        pdf.drawImage(str(path), 0, 0, width, height)
                        pdf.showPage()
                    pdf.save()
                else:
                    path, dpi = self.pages[0]
                    with Image.open(path) as im:
                        im.convert('RGB').save(stream, format=['PNG', 'JPEG'][self.format.currentIndex()-1],
                                               dpi=(dpi, dpi), **({'quality': 95} if self.format.currentIndex()==2 else {}))
            except BaseException:
                stream.close()
                dest.unlink(missing_ok=True)
                raise
        self.saved.append(dest)
        self.sequence += 1
        for path, _ in self.pages:
            path.unlink(missing_ok=True)
        self.pages.clear()

    def document_boundary(self):
        try:
            self.save_document()
            self.status.setText('Documento salvo. Coloque a primeira página do próximo documento.')
        except Exception as exc:
            self.status.setText(str(exc))
        self.controls()

    def finish_batch(self):
        try:
            self.save_document()
            self.success()
        except Exception as exc:
            self.status.setText(str(exc))

    def success(self):
        self.accept()

    def reject(self):
        if self.pending:
            if self.proc.state() != QProcess.ProcessState.NotRunning:
                self.proc.kill()
                self.proc.waitForFinished(3000)
        if self.pages and QMessageBox.question(self, 'Sair da digitalização',
                    'Descartar as páginas ainda não salvas?') != QMessageBox.StandardButton.Yes:
            return
        super().reject()
