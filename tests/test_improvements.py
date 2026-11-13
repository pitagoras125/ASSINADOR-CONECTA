import io
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from test_engine import material
from pypdf import PdfReader,PdfWriter
from pypdf.generic import RectangleObject
from placement import geometry,display_to_pdf,pdf_to_display,choose_placement,occupied,overlaps
from engine import sign_pdf,inspect_pdf
from declaration import make_declaration
from batch import sign_batch

@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_position_rotation_crop_and_cosign(material,rotation):
    pdf,pfx,d=material
    writer=PdfWriter(clone_from=pdf);writer.pages[0].cropbox=RectangleObject((20,30,575,800));writer.pages[0].rotate(rotation)
    src=d/'cropped.pdf'
    with src.open('wb') as f:writer.write(f)
    g=geometry(PdfReader(src).pages[0]);rect=(40,70,300,300*140/460);box=display_to_pdf(g,rect)
    assert pdf_to_display(g,box)==pytest.approx(rect)
    manual=d/'cpf.pdf';make_declaration(src,manual,'Pessoa Teste','52998224725','01/01/1990',page_index=0,box=box)
    registered=occupied(PdfReader(manual),0);assert registered[0]==pytest.approx(box)
    page,auto=choose_placement(manual);assert not overlaps(box,auto)
    digital=d/'digital.pdf';results=sign_pdf(manual,digital,pfx,'test-password',page_index=0,box=auto)
    assert results[0]['intact'] and results[0]['valid']
    second=d/'second.pdf';results=sign_pdf(digital,second,pfx,'test-password')
    assert len(results)==2 and all(r['intact'] and r['valid'] and r['allowed'] for r in results)
    assert second.read_bytes().startswith(digital.read_bytes())
    before=second.read_bytes()
    result=sign_pdf(second,d/'overlap.pdf',pfx,'test-password',page_index=0,box=box)
    assert all(r['intact'] and r['valid'] for r in result)
    assert second.read_bytes()==before


def test_batch_duplicate_names_failure_and_no_overwrite(material):
    pdf,pfx,d=material
    a=d/'a';b=d/'b';out=d/'out'
    for p in (a,b,out):p.mkdir()
    (a/'same.pdf').write_bytes(pdf.read_bytes());(b/'same.pdf').write_bytes(pdf.read_bytes());bad=d/'bad.pdf';bad.write_bytes(b'not PDF')
    (out/'same_assinado.pdf').write_bytes(b'preserve')
    rows=sign_batch([a/'same.pdf',bad,b/'same.pdf',a/'same.pdf'],out,method='cert',pfx_path=pfx,password='test-password')
    assert [r['status'] for r in rows]==['concluido','erro','concluido']
    assert Path(rows[0]['destination']).name=='same_assinado_2.pdf'
    assert Path(rows[2]['destination']).name=='same_assinado_3.pdf'
    assert (out/'same_assinado.pdf').read_bytes()==b'preserve'
    assert (a/'same.pdf').read_bytes()==pdf.read_bytes()
    assert all(inspect_pdf(r['destination'])[0]['valid'] for r in rows if r['status']=='concluido')


def test_cancel_batch_between_documents(material):
    pdf,pfx,d=material;out=d/'out';out.mkdir()
    other=d/'other.pdf';other.write_bytes(pdf.read_bytes());seen=[]
    def progress(i,total,name):seen.append(i)
    rows=sign_batch([pdf,other],out,method='cpf',name='Pessoa Teste',cpf='52998224725',birth='01/01/1990',progress=progress,cancelled=lambda:0 in seen)
    assert [r['status'] for r in rows]==['concluido','cancelado']
    assert len(list(out.glob('*.pdf')))==1


def test_invalid_position_and_page_are_rejected(material):
    pdf,pfx,d=material
    for page,box in [(99,(10,10,200,100)),(0,(-5,0,300,100)),(0,(0,0,float('nan'),100))]:
        with pytest.raises(ValueError):sign_pdf(pdf,d/'bad.pdf',pfx,'test-password',page_index=page,box=box)
        assert not (d/'bad.pdf').exists()
