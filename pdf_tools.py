"""Cria cópias novas; nenhuma operação altera um original."""
import io, os, tempfile
from pathlib import Path
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4, landscape

MAX_BYTES=200*1024*1024

def read_pdf(path):
    if Path(path).stat().st_size>MAX_BYTES: raise ValueError('O PDF excede 200 MB.')
    r=PdfReader(str(path))
    if r.is_encrypted: raise ValueError('Desbloqueie o PDF antes de organizar páginas.')
    if not r.pages: raise ValueError('PDF sem páginas.')
    return r

def signed(reader):
    def field(f):
        f=f.get_object()
        return (f.get('/FT')=='/Sig' and bool(f.get('/V'))) or any(field(k) for k in f.get('/Kids',[]))
    root=reader.trailer['/Root'];form=root.get('/AcroForm')
    return bool(form and any(field(f) for f in form.get_object().get('/Fields',[])))

def ensure_new(output,inputs):
    target=Path(output).resolve()
    if target in {Path(p).resolve() for p in inputs}: raise ValueError('Escolha outro nome: o original deve ser preservado.')
    if target.exists(): raise ValueError('Este arquivo já existe. Escolha um nome novo.')
    return target

def atomic_write(output,write):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.conecta-',suffix='.pdf',dir=output.parent)
    try:
        with os.fdopen(fd,'wb') as stream: write(stream)
        # Exclusive creation prevents an overwrite if a file appeared while processing.
        created=False
        try:
            with open(tmp,'rb') as src,open(output,'xb') as dst:
                created=True
                import shutil
                shutil.copyfileobj(src,dst)
        except Exception:
            if created:output.unlink(missing_ok=True)
            raise
    except Exception:
        # Do not delete a pre-existing destination on failure.
        raise
    finally: Path(tmp).unlink(missing_ok=True)

def parse_pages(text,count):
    result=[]
    try:
        for part in text.split(','):
            vals=part.strip().split('-')
            if len(vals)==1: items=[int(vals[0])]
            elif len(vals)==2:
                a,b=map(int,vals)
                if a>b: raise ValueError()
                items=range(a,b+1)
            else: raise ValueError()
            for n in items:
                if n<1 or n>count: raise ValueError()
                if n-1 not in result:result.append(n-1)
    except (ValueError,TypeError):raise ValueError(f'Informe páginas entre 1 e {count}, por exemplo: 1-3,5.') from None
    if not result:raise ValueError('Selecione ao menos uma página.')
    return result

def merge_pdfs(paths,output):
    if not 2<=len(paths)<=100:raise ValueError('Selecione entre 2 e 100 PDFs.')
    if sum(Path(p).stat().st_size for p in paths)>MAX_BYTES:raise ValueError('Os PDFs selecionados excedem 200 MB no total.')
    target=ensure_new(output,paths);writer=PdfWriter()
    try:
        for path in paths:
            reader=read_pdf(path)
            if signed(reader):raise ValueError('PDF assinado: juntar páginas retiraria a validade da assinatura na cópia. Use os originais sem assinatura.')
            writer.append(reader,import_outline=False)
        atomic_write(target,writer.write)
    finally:writer.close()
    return str(target)

def extract_pages(source,output,pages):
    target=ensure_new(output,[source]);reader=read_pdf(source)
    if signed(reader):raise ValueError('PDF assinado: separar páginas retiraria a validade da assinatura na cópia. Use o original sem assinatura.')
    selected=parse_pages(pages,len(reader.pages));writer=PdfWriter()
    try:
        for i in selected:writer.add_page(reader.pages[i])
        atomic_write(target,writer.write)
    finally:writer.close()
    return str(target)

def images_to_pdf(paths,output):
    if not 1<=len(paths)<=100:raise ValueError('Selecione entre 1 e 100 imagens.')
    target=ensure_new(output,paths)
    if sum(Path(p).stat().st_size for p in paths)>MAX_BYTES:raise ValueError('As imagens excedem 200 MB.')
    def write(stream):
        c=canvas.Canvas(stream);c.setCreator('Conecta PDF · Avante Sistemas')
        for path in paths:
            with Image.open(path) as raw:
                if raw.width*raw.height>40_000_000:raise ValueError('Uma imagem excede 40 megapixels.')
                im=ImageOps.exif_transpose(raw).convert('RGB');im.thumbnail((3000,3000))
                page=landscape(A4) if im.width>im.height else A4
                w,h=page;c.setPageSize(page);scale=min((w-48)/im.width,(h-48)/im.height)
                iw,ih=im.width*scale,im.height*scale
                c.drawImage(ImageReader(im),(w-iw)/2,(h-ih)/2,iw,ih);c.showPage()
        c.save()
    atomic_write(target,write);return str(target)
