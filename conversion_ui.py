from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from document_conversion import OFFICE, export_pdf, office_pdf


def convert(window, exporting=False):
    if exporting:
        source = window.path
        if not source:
            source, _ = QFileDialog.getOpenFileName(window, 'Selecionar PDF', '', 'PDF (*.pdf)')
        if not source:
            return
        formats = {'Texto (.txt)': 'txt', 'Páginas PNG (.zip)': 'png', 'Páginas JPEG (.zip)': 'jpeg'}
        label, ok = QInputDialog.getItem(window, 'Exportar PDF', 'Formato de saída', list(formats), editable=False)
        if not ok:
            return
        mode = formats[label]
        extension = 'txt' if mode == 'txt' else 'zip'
    else:
        pattern = ' '.join('*.' + item for item in OFFICE)
        source, _ = QFileDialog.getOpenFileName(window, 'Converter documento', '', f'Documentos ({pattern})')
        if not source:
            return
        extension = 'pdf'
    target, _ = QFileDialog.getSaveFileName(window, 'Salvar conversão', str(Path(source).with_suffix('.' + extension)), f'Arquivo (*.{extension})')
    if not target:
        return
    if not target.lower().endswith('.' + extension):
        target += '.' + extension
    def finished(_):
        if exporting:
            QMessageBox.information(window, 'Conversão concluída', target)
        else:
            window.load(target)
    window.run_job(lambda: export_pdf(source, target, mode) if exporting else office_pdf(source, target), finished)
