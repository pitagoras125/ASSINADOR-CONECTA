import sys,hashlib,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from test_engine import material
from pypdf import PdfWriter,PdfReader
from PIL import Image
from pdf_tools import merge_pdfs,extract_pages,images_to_pdf,parse_pages
from desktop_updates import validate_manifest,canonical
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from scanner import detect_document,rectify,StableCapture
import numpy as np,cv2

def make_pdf(path,count):
    w=PdfWriter()
    for i in range(count):w.add_blank_page(width=300+i,height=400)
    with open(path,'wb') as f:w.write(f)

def test_merge_extract_preserves_originals(tmp_path):
    a=tmp_path/'a.pdf';b=tmp_path/'b.pdf';make_pdf(a,2);make_pdf(b,1);before=a.read_bytes()
    merged=tmp_path/'merged.pdf';merge_pdfs([b,a],merged)
    assert len(PdfReader(merged).pages)==3
    out=tmp_path/'subset.pdf';extract_pages(merged,out,'3,1')
    assert [float(p.mediabox.width) for p in PdfReader(out).pages]==[301,300]
    assert a.read_bytes()==before
    with pytest.raises(ValueError):merge_pdfs([a,b],a)
    with pytest.raises(ValueError):extract_pages(a,out,'1')

@pytest.mark.parametrize('text',['0','4','2-1','a','1,,2','-2',''])
def test_invalid_ranges(text):
    with pytest.raises(ValueError):parse_pages(text,3)

def test_images_and_corruption(tmp_path):
    image=tmp_path/'a.png';Image.new('RGB',(80,120),'white').save(image);before=image.read_bytes()
    out=tmp_path/'images.pdf';images_to_pdf([image,image],out)
    assert len(PdfReader(out).pages)==2 and image.read_bytes()==before
    bad=tmp_path/'bad.png';bad.write_bytes(b'bad')
    with pytest.raises(Exception):images_to_pdf([bad],tmp_path/'bad.pdf')
    assert not (tmp_path/'bad.pdf').exists()

def test_signed_manifest_tamper_and_downgrade():
    key=Ed25519PrivateKey.generate();pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    payload=dict(app='conecta-pdf-windows',version='1.0.1',url='https://github.com/pitagoras125/assinador-conecta-atualizacoes/releases/download/desktop-v1.0.1/setup.exe',size=100,sha256='a'*64)
    envelope=dict(payload=payload,signature=base64.b64encode(key.sign(canonical(payload))).decode())
    assert validate_manifest(envelope,pub)['version']=='1.0.1'
    assert validate_manifest(envelope,pub,current='1.0.1') is None
    payload['size']=101
    with pytest.raises(Exception):validate_manifest(envelope,pub)

def test_document_detection_and_capture_gate():
    frame=np.zeros((700,900,3),np.uint8);cv2.rectangle(frame,(150,100),(750,600),(255,255,255),-1)
    points=detect_document(frame);assert points is not None
    cropped=rectify(frame,points);assert cropped.shape[0]>450 and cropped.shape[1]>550
    gate=StableCapture();assert not gate.update(points,0);assert gate.update(points,1.3);assert not gate.update(points,4)
    gate.update(None,5);assert not gate.update(points,6);assert gate.update(points,7.3)

def test_signed_pdf_organization_is_rejected(material):
    from engine import sign_pdf
    pdf,pfx,d=material;certified=d/'certified.pdf';sign_pdf(pdf,certified,pfx,'test-password');before=certified.read_bytes()
    with pytest.raises(ValueError,match='assinado'):extract_pages(certified,d/'extract.pdf','1')
    with pytest.raises(ValueError,match='assinado'):merge_pdfs([pdf,certified],d/'merge.pdf')
    assert certified.read_bytes()==before and not (d/'extract.pdf').exists() and not (d/'merge.pdf').exists()

def test_download_rejects_modified_installer(monkeypatch):
    import desktop_updates,io
    monkeypatch.setattr(desktop_updates,'open_url',lambda url:io.BytesIO(b'corrupted'))
    with pytest.raises(ValueError,match='integridade'):desktop_updates.download_update({'url':'unused','size':9,'sha256':hashlib.sha256(b'expected!').hexdigest()})
