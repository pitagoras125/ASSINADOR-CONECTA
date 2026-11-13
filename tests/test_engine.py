import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from reportlab.pdfgen import canvas
from engine import sign_pdf, inspect_pdf

@pytest.fixture
def material(tmp_path):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'CERTIFICADO DE TESTE - NAO ICP')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=10)).add_extension(x509.BasicConstraints(ca=False,path_length=None),True).add_extension(x509.KeyUsage(True,True,False,False,False,False,False,None,None),True).sign(key,hashes.SHA256()))
    pfx=tmp_path/'test.pfx';pfx.write_bytes(pkcs12.serialize_key_and_certificates(b'test',key,cert,None,serialization.BestAvailableEncryption(b'test-password')))
    pdf=tmp_path/'original.pdf';c=canvas.Canvas(str(pdf),pageCompression=0);c.drawString(50,700,'CONTEUDO ORIGINAL 123456');c.save()
    return pdf,pfx,tmp_path

def test_sign_and_cosign(material):
    pdf,pfx,d=material; original=pdf.read_bytes()
    first=d/'first.pdf';second=d/'second.pdf'
    r=sign_pdf(pdf,first,pfx,'test-password');assert len(r)==1 and r[0]['intact'] and r[0]['valid'] and not r[0]['trusted']
    r=sign_pdf(first,second,pfx,'test-password');assert len(r)==2 and all(x['intact'] and x['valid'] and x['allowed'] for x in r)
    assert second.read_bytes().startswith(first.read_bytes())
    assert pdf.read_bytes()==original

def test_password_and_overwrite(material):
    pdf,pfx,d=material
    with pytest.raises(ValueError,match='senha'):sign_pdf(pdf,d/'bad.pdf',pfx,'wrong')
    assert not (d/'bad.pdf').exists()
    with pytest.raises(ValueError):sign_pdf(pdf,pdf,pfx,'test-password')
    out=d/'exists.pdf';out.write_bytes(b'preserve')
    with pytest.raises(ValueError):sign_pdf(pdf,out,pfx,'test-password')
    assert out.read_bytes()==b'preserve'

def test_tampering(material):
    pdf,pfx,d=material;out=d/'signed.pdf';sign_pdf(pdf,out,pfx,'test-password')
    raw=out.read_bytes();assert b'CONTEUDO ORIGINAL' in raw
    out.write_bytes(raw.replace(b'CONTEUDO ORIGINAL',b'CONTEUDO ALTERADO'))
    result=inspect_pdf(out);assert not result[0]['intact']
    with pytest.raises(ValueError):sign_pdf(out,d/'next.pdf',pfx,'test-password')

def test_expired_certificate(material):
    pdf,pfx,d=material
    key,old,_=pkcs12.load_key_and_certificates(pfx.read_bytes(),b'test-password')
    now=datetime.now(timezone.utc)
    expired=(x509.CertificateBuilder().subject_name(old.subject).issuer_name(old.issuer).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=10)).not_valid_after(now-timedelta(days=1)).add_extension(x509.KeyUsage(True,True,False,False,False,False,False,None,None),True).sign(key,hashes.SHA256()))
    pfx.write_bytes(pkcs12.serialize_key_and_certificates(b'expired',key,expired,None,serialization.BestAvailableEncryption(b'test-password')))
    with pytest.raises(ValueError,match='vencido'):sign_pdf(pdf,d/'expired.pdf',pfx,'test-password')
    assert not (d/'expired.pdf').exists()

def test_windows_bridge_contract_and_visible_stamp(material,monkeypatch):
    import base64
    from cryptography.hazmat.primitives.asymmetric import padding
    import windows_store
    from pypdf import PdfReader
    pdf,pfx,d=material
    key,cert,_=pkcs12.load_key_and_certificates(pfx.read_bytes(),b'test-password')
    der=base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()
    item={'thumbprint':'TEST','der':der,'chain':[der]}
    def mock_call(payload):
        assert payload['thumbprint']=='TEST'
        signed=key.sign(base64.b64decode(payload['data']),padding.PKCS1v15(),hashes.SHA256())
        return {'signature':base64.b64encode(signed).decode(),'chain':[der]}
    monkeypatch.setattr(windows_store,'call_windows',mock_call)
    out=d/'windows_mock.pdf';result=sign_pdf(pdf,out,windows_cert=item)
    assert result[0]['valid'] and result[0]['intact']
    annot=PdfReader(out).pages[-1]['/Annots'][0].get_object()
    assert '/AP' in annot and annot['/Rect'][2]>annot['/Rect'][0]

def test_cpf_declaration_and_validation(material):
    from declaration import make_declaration
    from pypdf import PdfReader
    pdf,pfx,d=material
    out=d/'declaration.pdf'
    make_declaration(pdf,out,'Pessoa de Teste','529.982.247-25','01/01/1990',True)
    reader=PdfReader(out);assert len(reader.pages)==1
    text=reader.pages[-1].extract_text();assert '529.982.247-25' in text and '01/01/1990' not in text
    assert not inspect_pdf(out)
    second=d/'declaration2.pdf'
    make_declaration(out,second,'Outra Pessoa','52998224725','01/01/1990',True)
    assert len(PdfReader(second).pages)==1
    assert PdfReader(second).pages[0].extract_text().count('Assinado eletronicamente por')==2
    with pytest.raises(ValueError,match='CPF'):make_declaration(pdf,d/'invalid.pdf','Pessoa Teste','11111111111','01/01/1990',True)
    signed=d/'signed.pdf';sign_pdf(pdf,signed,pfx,'test-password')
    with pytest.raises(ValueError,match='preservar'):make_declaration(signed,d/'no.pdf','Pessoa Teste','52998224725','01/01/1990',True)
