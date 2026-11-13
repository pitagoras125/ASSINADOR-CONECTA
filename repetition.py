"""Repetição atômica: valida todas as posições antes de assinar e publica uma cópia."""
from pathlib import Path
import tempfile
import shutil
from pypdf import PdfReader
from placement import geometry,display_to_pdf,pdf_to_display,validate_box

def parse_pages(text,count):
    result=set()
    try:
        for item in text.split(','):
            bounds=item.strip().split('-')
            if len(bounds)==1:result.add(int(bounds[0])-1)
            elif len(bounds)==2:
                a,b=map(int,bounds)
                if a>b or a<1 or b>count:raise ValueError()
                result.update(range(a-1,b))
            else:raise ValueError()
        if not result or min(result)<0 or max(result)>=count:raise ValueError()
    except (ValueError,TypeError):raise ValueError('Páginas inválidas. Exemplo: 1,3-5. Use apenas páginas existentes.') from None
    return sorted(result)

def plan(source,page_index,box,pages,rubrics=False):
    reader=PdfReader(str(source));selected=parse_pages(pages,len(reader.pages))
    g=geometry(reader.pages[page_index]);x,y,w,h=pdf_to_display(g,box)
    result=[]
    for i in selected:
        target=geometry(reader.pages[i]);small=rubrics and i!=selected[-1]
        factor=.6 if small else 1
        rect=[x,y,w*factor,h*factor]
        # Repeat the same physical size and relative location, clamped to the visible page.
        rect[0]=x/g['width']*target['width'];rect[1]=y/g['height']*target['height']
        rect[0]=min(rect[0],target['width']-rect[2]);rect[1]=min(rect[1],target['height']-rect[3])
        b=validate_box(reader,i,display_to_pdf(target,rect));result.append(dict(page_index=i,box=b,rubric=small))
    return result

def repeat(operation,source,destination,*,page_index,box,pages,rubrics,kwargs):
    source,destination=Path(source),Path(destination)
    if source.resolve()==destination.resolve() or destination.exists():raise ValueError('Escolha um novo arquivo de saída.')
    placements=plan(source,page_index,box,pages,rubrics)
    with tempfile.TemporaryDirectory(prefix='.conecta-',dir=destination.parent) as folder:
        current=source;result=[]
        for n,item in enumerate(placements):
            target=Path(folder)/f'{n}.pdf';result=operation(current,target,**kwargs,**item);current=target
        with open(destination,'xb') as out:
            try:
                with open(current,'rb') as stream:shutil.copyfileobj(stream,out)
            except Exception:
                out.close();destination.unlink(missing_ok=True);raise
    return result
