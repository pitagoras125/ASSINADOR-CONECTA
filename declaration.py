"""Chancela declaratória local. Não autentica identidade nem gera assinatura ICP."""
from datetime import datetime,date
from pathlib import Path
import io
from engine import inspect_pdf

def validate_cpf(value):
    cpf=''.join(c for c in value if c.isdigit())
    if len(cpf)!=11 or len(set(cpf))==1:raise ValueError('CPF inválido.')
    for n in (9,10):
        digit=(sum(int(cpf[i])*(n+1-i) for i in range(n))*10)%11
        if int(cpf[n])!=(0 if digit==10 else digit):raise ValueError('CPF inválido.')
    return cpf

def make_declaration(source,destination,name,cpf,birth,consent=True,*,page_index=None,box=None,pages=None,rubrics=False,rubric=False):
    if pages is not None:
        from repetition import repeat
        return repeat(make_declaration,source,destination,page_index=page_index,box=box,pages=pages,rubrics=rubrics,kwargs=dict(name=name,cpf=cpf,birth=birth,consent=consent))
    if not consent:raise ValueError('É necessário confirmar a declaração de autoria.')
    if len(name.strip().split())<2:raise ValueError('Informe o nome completo.')
    cpf=validate_cpf(cpf)
    try: birthday=datetime.strptime(birth,'%d/%m/%Y').date()
    except ValueError:raise ValueError('Data de nascimento inválida. Use DD/MM/AAAA.') from None
    if birthday>date.today() or birthday.year<1900:raise ValueError('Data de nascimento inválida.')
    source,destination=Path(source),Path(destination)
    if source.resolve()==destination.resolve() or destination.exists():raise ValueError('Escolha um novo arquivo de saída.')
    if inspect_pdf(source):raise ValueError('A chancela declaratória não será adicionada a PDF já assinado digitalmente, para preservar as assinaturas.')
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import NameObject,NumberObject
    reader=PdfReader(str(source))
    if reader.is_encrypted:raise ValueError('PDF com senha não suportado.')
    if not reader.pages:raise ValueError('PDF sem páginas.')
    writer=PdfWriter(clone_from=reader)
    from placement import choose_placement,geometry,seal_transform
    page_index,box=choose_placement(source,page_index,box)
    page=writer.pages[page_index]
    index=int(writer._root_object.get('/ConectaChancelas',0))
    formatted=f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
    import hashlib,uuid
    from seal import seal_pdf
    pdf=seal_pdf(name,formatted,'cpf','PROT-'+uuid.uuid4().hex[:20].upper(),hashlib.sha256(source.read_bytes()).hexdigest(),rubric=rubric)
    overlay=PdfReader(io.BytesIO(pdf)).pages[0]
    from pypdf import Transformation
    overlay.add_transformation(Transformation(ctm=seal_transform(box,geometry(page)['rotation'])))
    from pypdf.generic import RectangleObject
    overlay.mediabox=RectangleObject(page.mediabox)
    overlay.cropbox=RectangleObject(page.cropbox)
    page.merge_page(overlay)
    writer._root_object[NameObject('/ConectaChancelas')]=NumberObject(index+1)
    from pypdf.generic import ArrayObject,DictionaryObject,FloatObject
    records=writer._root_object.get('/ConectaPlacements',ArrayObject())
    records.append(DictionaryObject({NameObject('/Page'):NumberObject(page_index),NameObject('/Rect'):ArrayObject([FloatObject(v) for v in box])}))
    writer._root_object[NameObject('/ConectaPlacements')]=records
    output=io.BytesIO();writer.write(output)
    output.seek(0)
    if len(PdfReader(output).pages)!=len(reader.pages):raise ValueError('Falha ao conferir o PDF gerado.')
    with open(destination,'xb') as stream:
        try:stream.write(output.getvalue())
        except Exception:
            stream.close();destination.unlink(missing_ok=True);raise
    return []
