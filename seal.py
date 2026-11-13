"""Um único desenho de chancela para os dois métodos."""
import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from branding import logo_image

def seal_pdf(name,identifier,method,protocol,digest,issuer='',when=None,rubric=False):
    import qrcode
    width,height=460,140
    buf=io.BytesIO();c=canvas.Canvas(buf,pagesize=(width,height))
    c.setFillColorRGB(1,1,1);c.setStrokeColorRGB(.11,.15,.20);c.setLineWidth(.7);c.roundRect(.5,.5,459,139,8,fill=1,stroke=1)
    logo=logo_image();c.saveState();c.setFillAlpha(.045);c.drawImage(ImageReader(logo),185,10,245,83,mask='auto',preserveAspectRatio=True);c.restoreState()
    def text(s,x,y,size=7,font='Helvetica',color=(.13,.20,.30),maxwidth=345):
        while stringWidth(s,font,size)>maxwidth and size>3:size-=.2
        c.setFillColorRGB(*color);c.setFont(font,size);c.drawString(x,y,s)
    c.setFillColorRGB(.025,.04,.06);c.roundRect(12,113,126,15,3,fill=1,stroke=0)
    c.setFillColorRGB(0,.8,.62);c.circle(20,120.5,2,fill=1,stroke=0)
    text('CERTIFICADO DIGITAL' if method=='cert' else 'ASSINATURA COM CPF',26,118,6.3,'Helvetica-Bold',(1,1,1),106)
    text('RUBRICA ASSINADOR CONECTA' if rubric else 'CHANCELA ASSINADOR CONECTA',146,118,7,'Helvetica-Bold',maxwidth=230)
    text('Assinado digitalmente por' if method=='cert' else 'Assinado eletronicamente por',12,99,7)
    text(name.upper(),12,86,9,'Helvetica-Bold',maxwidth=351)
    text('Identificador: '+identifier,12,74,7,maxwidth=351)
    text(('Emissor: '+issuer) if method=='cert' else 'Método: CPF e data de nascimento informados pelo signatário',12,63,6.5,maxwidth=351)
    c.setFillColorRGB(.956,.968,.985);c.setStrokeColorRGB(.86,.90,.95);c.roundRect(12,11,353,43,3,fill=1,stroke=1)
    text('PROTOCOLO',19,43,6,'Courier',(.40,.49,.61),63)
    text(protocol,91,43,6.5,'Courier-Bold',maxwidth=265)
    text('SHA-256 ORIGEM',19,30,5.8,'Courier',(.40,.49,.61),69)
    text(digest,91,30,5.7,'Courier',maxwidth=265)
    text('DATA LOCAL',19,18,6,'Courier',(.40,.49,.61),63)
    when=when or datetime.now().astimezone().strftime('%d/%m/%Y %H:%M:%S %z')
    text(when,91,18,6.5,'Courier',maxwidth=265)
    payload='ASSINADOR CONECTA\n'+protocol+'\nSHA256 origem: '+digest+'\nMetodo: '+('certificado digital' if method=='cert' else 'CPF informado')
    qr=qrcode.make(payload);c.drawImage(ImageReader(qr.get_image()),380,56,65,65,mask='auto')
    text('DADOS DO REGISTRO',378,44,5.1,'Helvetica',(.40,.49,.61),70)
    text('QR informativo',385,35,5.4,'Helvetica',(.40,.49,.61),65)
    c.save();return buf.getvalue()

# A aparência do certificado incorpora exatamente o mesmo PDF usado no modo CPF.
from dataclasses import dataclass
from pyhanko.stamp import BaseStamp,BaseStampStyle
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.content import ResourceType
from pyhanko.pdf_utils.generic import pdf_name

class UnifiedStamp(BaseStamp):
    def _render_inner_content(self):
        imported=self.writer.import_page_as_xobject(PdfFileReader(io.BytesIO(self.style.pdf_bytes)))
        self.set_resource(ResourceType.XOBJECT,pdf_name('/ConectaSeal'),imported)
        from placement import seal_transform
        matrix=seal_transform((0,0,self.box.width,self.box.height),self.style.rotation)
        return [b'q %g %g %g %g %g %g cm /ConectaSeal Do Q' % matrix]

@dataclass(frozen=True)
class UnifiedStampStyle(BaseStampStyle):
    pdf_bytes: bytes=b''
    rotation: int=0
    border_width: int=0
    def create_stamp(self,writer,box,text_params):
        return UnifiedStamp(writer=writer,style=self,box=box)
