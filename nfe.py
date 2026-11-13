"""Visualização local de NF-e 55. Não consulta nem altera a SEFAZ/XML."""
from pathlib import Path
import hashlib
from defusedxml import ElementTree as ET
NS={'n':'http://www.portalfiscal.inf.br/nfe'}

def read_nfe(path):
    with Path(path).open('rb') as stream:raw=stream.read(20*1024*1024+1)
    if len(raw)>20*1024*1024: raise ValueError('XML excede o limite de 20 MB.')
    root=ET.fromstring(raw,forbid_dtd=True)
    tag=root.tag.split('}')[-1]
    if tag not in ('nfeProc','NFe'): raise ValueError('Abra o XML completo da NF-e modelo 55. Resumos e eventos não geram DANFE.')
    nodes=root.findall('.//n:infNFe',NS)
    if len(nodes)!=1: raise ValueError('O XML deve conter exatamente uma NF-e completa.')
    info=nodes[0]
    def val(p): return info.findtext(p,default='',namespaces=NS)
    if val('n:ide/n:mod')!='55': raise ValueError('Somente NF-e modelo 55 é suportada. NFC-e e NFS-e não são aceitas.')
    if info.get('versao')!='4.00': raise ValueError('Esta versão lê NF-e no leiaute 4.00.')
    key=info.get('Id','').removeprefix('NFe')
    if len(key)!=44 or not key.isdigit() or key[20:22]!='55': raise ValueError('Chave de acesso inválida.')
    total=sum(int(c)*(2+i%8) for i,c in enumerate(reversed(key[:-1])))
    digit=11-total%11;digit=0 if digit>=10 else digit
    if int(key[-1])!=digit: raise ValueError('Dígito verificador da chave de acesso inválido.')
    if not info.findall('n:det',NS) or not val('n:emit/n:xNome') or not val('n:total/n:ICMSTot/n:vNF'): raise ValueError('XML incompleto: faltam emitente, itens ou totais.')
    protocol=root.find('n:protNFe/n:infProt',NS)
    if protocol is not None and protocol.findtext('n:chNFe','',NS)!=key: raise ValueError('Protocolo de outra chave de acesso.')
    status=protocol.findtext('n:cStat','',NS) if protocol is not None else ''
    return raw,dict(key=key,number=val('n:ide/n:nNF'),issuer=val('n:emit/n:xNome'),total=val('n:total/n:ICMSTot/n:vNF'),environment=val('n:ide/n:tpAmb'),protocol_status=status,sha256=hashlib.sha256(raw).hexdigest())

def render_nfe(source,destination):
    raw,meta=read_nfe(source)
    from brazilfiscalreport.danfe import Danfe
    # Parse bytes first (honors XML encoding), then serialize to Unicode for renderer.
    from xml.etree.ElementTree import tostring
    xml=tostring(ET.fromstring(raw,forbid_dtd=True),encoding='unicode')
    result=bytes(Danfe(xml=xml).output())
    # Never suggest authorization when a valid authorization protocol is absent.
    if meta['protocol_status'] not in ('100','150'):
        import io
        from pypdf import PdfReader,PdfWriter
        from reportlab.pdfgen.canvas import Canvas
        reader=PdfReader(io.BytesIO(result)); writer=PdfWriter()
        for page in reader.pages:
            buf=io.BytesIO();c=Canvas(buf,pagesize=(float(page.mediabox.width),float(page.mediabox.height)))
            c.setFillColorRGB(.65,0,0);c.setFont('Helvetica-Bold',9)
            c.drawCentredString(float(page.mediabox.width)/2,12,'SEM PROTOCOLO DE AUTORIZAÇÃO VÁLIDO NO XML');c.save()
            page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0]);writer.add_page(page)
        buf=io.BytesIO();writer.write(buf);result=buf.getvalue()
    destination=Path(destination)
    if destination.resolve()==Path(source).resolve(): raise ValueError('O XML original não pode ser substituído.')
    with destination.open('xb') as stream:stream.write(result)
    return meta
