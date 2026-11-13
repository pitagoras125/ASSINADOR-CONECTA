"""Geometria única para prévia, chancelas manuais e campos de assinatura."""
from math import isfinite
from pypdf import PdfReader


def geometry(page):
    r=tuple(float(v) for v in page.cropbox)
    rotation=int(page.get('/Rotate',0))%360
    if rotation not in (0,90,180,270):raise ValueError('Rotação de página não suportada.')
    w,h=r[2]-r[0],r[3]-r[1]
    return dict(crop=r,rotation=rotation,width=h if rotation in (90,270) else w,height=w if rotation in (90,270) else h)


def display_to_pdf(g,rect):
    x,y,w,h=rect;x0,y0,x1,y1=g['crop'];W,H=x1-x0,y1-y0
    def point(u,v):
        angle=g['rotation']
        a,b=(u,H-v) if angle==0 else (v,u) if angle==90 else (W-u,v) if angle==180 else (W-v,H-u)
        return a+x0,b+y0
    points=[point(x,y),point(x+w,y),point(x,y+h),point(x+w,y+h)]
    return (min(a for a,b in points),min(b for a,b in points),max(a for a,b in points),max(b for a,b in points))


def pdf_to_display(g,box):
    x0,y0,x1,y1=g['crop'];W,H=x1-x0,y1-y0
    def point(x,y):
        x,y=x-x0,y-y0;r=g['rotation']
        return (x,H-y) if r==0 else (y,x) if r==90 else (W-x,y) if r==180 else (H-y,W-x)
    x,y,X,Y=box;p=[point(x,y),point(X,y),point(x,Y),point(X,Y)]
    left,top=min(a for a,b in p),min(b for a,b in p)
    return left,top,max(a for a,b in p)-left,max(b for a,b in p)-top


def overlaps(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>1 and min(a[3],b[3])-max(a[1],b[1])>1


def occupied(reader,page_index):
    result=[]
    page=reader.pages[page_index]
    for ref in page.get('/Annots',[]):
        ann=ref.get_object();parent=ann.get('/Parent',ann).get_object()
        if ann.get('/FT',parent.get('/FT'))=='/Sig':
            rect=tuple(float(v) for v in ann.get('/Rect',[0,0,0,0]))
            if rect[2]>rect[0] and rect[3]>rect[1]:result.append(rect)
    root=reader.trailer['/Root']
    records=root.get('/ConectaPlacements',[])
    for rec in records:
        rec=rec.get_object()
        if int(rec['/Page'])==page_index:result.append(tuple(float(v) for v in rec['/Rect']))
    # Compatibilidade com as chancelas anteriores que não guardavam retângulos.
    legacy=max(0,int(root.get('/ConectaChancelas',0))-len(records))
    if page_index==len(reader.pages)-1:
        g=geometry(page);w=min(460,g['width']-50);h=w*140/460
        for i in range(legacy):result.append(display_to_pdf(g,(25,g['height']-25-h-i*(h+10),w,h)))
    return result


def validate_box(reader,page_index,box):
    if not 0<=page_index<len(reader.pages):raise ValueError('A página escolhida não existe neste PDF.')
    if len(box)!=4 or not all(isfinite(float(v)) for v in box):raise ValueError('Posição de chancela inválida.')
    box=tuple(float(v) for v in box);g=geometry(reader.pages[page_index]);x,y,X,Y=g['crop']
    if box[0]<x-.1 or box[1]<y-.1 or box[2]>X+.1 or box[3]>Y+.1 or min(box[2]-box[0],box[3]-box[1])<35:
        raise ValueError('A chancela precisa ficar inteiramente dentro da página.')
    return box


def choose_placement(path,page_index=None,box=None):
    reader=PdfReader(str(path))
    if reader.is_encrypted:raise ValueError('PDF protegido por senha não suportado.')
    page_index=len(reader.pages)-1 if page_index is None else page_index
    if not 0<=page_index<len(reader.pages):raise ValueError('A página escolhida não existe neste PDF.')
    if box is not None:return page_index,validate_box(reader,page_index,box)
    g=geometry(reader.pages[page_index]);w=min(460,g['width']-50);h=w*140/460
    if w<200:raise ValueError('Página pequena demais para a chancela.')
    y=g['height']-25-h
    while y>=25:
        candidate=display_to_pdf(g,(25,y,w,h))
        if not any(overlaps(candidate,r) for r in occupied(reader,page_index)):
            return page_index,validate_box(reader,page_index,candidate)
        y-=h+10
    raise ValueError('Sem espaço livre para outra chancela. Escolha outra página com o mouse.')


def seal_transform(box,rotation):
    x,y,X,Y=box;w,h=X-x,Y-y
    return (w/460,0,0,h/140,x,y) if rotation==0 else (0,h/460,-w/140,0,X,y) if rotation==90 else (-w/460,0,0,-h/140,X,Y) if rotation==180 else (0,-h/460,w/140,0,x,Y)
