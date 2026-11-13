from pathlib import Path
import hashlib,copy
import pytest
from nfe import read_nfe,render_nfe
from test_engine import material
from engine import sign_pdf,inspect_pdf
from cpf_protected import make_protected_declaration
from pypdf import PdfReader
FIXTURE=Path(__file__).parent/'fixtures/nfe55.xml'

def test_nfe_original_and_pdf(tmp_path):
    original=FIXTURE.read_bytes();out=tmp_path/'nfe.pdf';meta=render_nfe(FIXTURE,out)
    assert FIXTURE.read_bytes()==original
    text=''.join(p.extract_text() for p in PdfReader(out).pages)
    assert 'DANFE' in text and '300,00' in text and meta['key'] in text.replace(' ','')
    assert 'SEM PROTOCOLO' in text
    with pytest.raises(FileExistsError):render_nfe(FIXTURE,out)

@pytest.mark.parametrize('change',[lambda s:s.replace('<mod>55</mod>','<mod>65</mod>'),lambda s:s.replace('versao="4.00"','versao="3.10"'),lambda s:'<resNFe xmlns="http://www.portalfiscal.inf.br/nfe"/>',lambda s:'<!DOCTYPE x [<!ENTITY test SYSTEM "file:///etc/passwd">]><NFe>&test;</NFe>'])
def test_reject_other_and_unsafe_xml(tmp_path,change):
    src=tmp_path/'bad.xml';src.write_text(change(FIXTURE.read_text()))
    with pytest.raises(Exception):read_nfe(src)

def test_multiple_pages(tmp_path):
    import xml.etree.ElementTree as ET
    ns='{http://www.portalfiscal.inf.br/nfe}';root=ET.fromstring(FIXTURE.read_bytes());info=root.find('.//'+ns+'infNFe');item=info.find(ns+'det')
    for i in range(2,100):
        new=copy.deepcopy(item);new.set('nItem',str(i));new.find(ns+'prod/'+ns+'cProd').text=str(i);info.insert(list(info).index(info.find(ns+'total')),new)
    src=tmp_path/'multi.xml';ET.ElementTree(root).write(src,encoding='utf-8',xml_declaration=True);out=tmp_path/'multi.pdf';render_nfe(src,out)
    assert len(PdfReader(out).pages)>1
    text=''.join(p.extract_text() for p in PdfReader(out).pages);assert '99' in text

def test_cpf_protected_and_tamper(material):
    src,pfx,d=material;before=src.read_bytes();out=d/'protected.pdf'
    make_protected_declaration(src,out,'Pessoa Teste','52998224725','01/01/1990')
    results=inspect_pdf(out);assert results[0]['intact'] and results[0]['valid'] and not results[0]['trusted'];assert 'SELO LOCAL' in results[0]['signer'];assert src.read_bytes()==before
    raw=out.read_bytes();assert b'/Reason' in raw
    out.write_bytes(raw.replace(b'Selo',b'SALO',1));assert not inspect_pdf(out)[0]['intact']

def test_cpf_already_signed_preserved(material):
    src,pfx,d=material;signed=d/'signed.pdf';sign_pdf(src,signed,pfx,'test-password');before=signed.read_bytes();receipt=d/'receipt.pdf'
    make_protected_declaration(signed,receipt,'Pessoa Teste','52998224725','01/01/1990')
    assert signed.read_bytes()==before and inspect_pdf(signed)[0]['intact']
    text=''.join(p.extract_text() for p in PdfReader(receipt).pages)
    assert hashlib.sha256(before).hexdigest() in text.replace('\n','')
    assert inspect_pdf(receipt)[0]['intact']
