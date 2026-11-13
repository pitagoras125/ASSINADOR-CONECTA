from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from zipfile import ZipFile
from io import BytesIO

from pdf_tools import ensure_new, atomic_write, read_pdf

OFFICE = 'doc docx odt rtf txt xls xlsx ods csv ppt pptx odp'.split()


def office_pdf(source, target):
    source = Path(source).resolve()
    target = ensure_new(target, [source])
    if source.suffix.lower()[1:] not in OFFICE:
        raise ValueError('Formato de origem incompatível.')
    executable = shutil.which('soffice')
    for variable in ('ProgramFiles', 'ProgramFiles(x86)'):
        candidate = Path(os.environ.get(variable, '')) / 'LibreOffice/program/soffice.exe'
        if not executable and candidate.is_file():
            executable = str(candidate.resolve())
    if not executable:
        raise ValueError('Instale o LibreOffice para converter documentos do Office neste computador.')
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        subprocess.run([executable, '-env:UserInstallation=' + (root/'profile').as_uri(),
                        '--headless', '--convert-to', 'pdf', '--outdir', folder, str(source)],
                       timeout=180, check=True, capture_output=True)
        result = root / (source.stem + '.pdf')
        read_pdf(result)
        with result.open('rb') as incoming:
            atomic_write(target, lambda out: shutil.copyfileobj(incoming, out))


def export_pdf(source, target, mode):
    target = ensure_new(target, [source])
    if mode == 'txt':
        pages = read_pdf(source).pages
        text = '\n\f\n'.join(page.extract_text() or '' for page in pages)
        if not text.strip():
            raise ValueError('Este PDF não contém texto selecionável.')
        atomic_write(target, lambda stream: stream.write(text.encode('utf-8')))
        return
    if mode not in ('png', 'jpeg'):
        raise ValueError('Formato de saída incompatível.')
    import pypdfium2 as pdfium
    def write(stream):
        with pdfium.PdfDocument(str(source)) as document, ZipFile(stream, 'w') as archive:
            for index in range(len(document)):
                page = document[index]
                try:
                    scale = min(2.0, 4000 / max(page.get_size()))
                    bitmap = page.render(scale=scale, draw_annots=True)
                    try:
                        data = BytesIO()
                        bitmap.to_pil().convert('RGB').save(data, format=mode.upper())
                        archive.writestr(f'pagina-{index + 1:04}.{mode}', data.getvalue())
                    finally:
                        bitmap.close()
                finally:
                    page.close()
    atomic_write(target, write)
