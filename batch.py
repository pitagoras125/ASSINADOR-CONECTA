"""Lote sequencial: resultados por arquivo, sem sobrescrita e cancelamento entre PDFs."""
from pathlib import Path
from engine import sign_pdf
from cpf_protected import make_protected_declaration as make_declaration


def available_output(folder,source,suffix):
    stem=Path(source).stem
    candidate=folder/(stem+suffix+'.pdf');n=2
    while candidate.exists():
        candidate=folder/(stem+suffix+f'_{n}.pdf');n+=1
    return candidate


def sign_batch(sources,folder,*,method,pfx_path=None,password='',windows_cert=None,name='',cpf='',birth='',placements=None,visible=True,progress=None,cancelled=None):
    folder=Path(folder)
    if not folder.is_dir():raise ValueError('Escolha uma pasta de saída existente.')
    if method not in ('cert','cpf'):raise ValueError('Método de assinatura desconhecido.')
    sources=list(dict.fromkeys(str(Path(p).resolve()) for p in sources))
    results=[];placements=placements or {}
    for i,source in enumerate(sources):
        if cancelled and cancelled():
            results.extend(dict(source=p,status='cancelado',destination=None) for p in sources[i:]);break
        if progress:progress(i,len(sources),Path(source).name)
        destination=available_output(folder,source,'_assinado' if method=='cert' else '_cpf')
        placement=placements.get(str(Path(source).resolve()),{})
        try:
            if method=='cert':
                signatures=sign_pdf(source,destination,pfx_path,password,windows_cert=windows_cert,visible=visible,**placement)
                count=len(signatures)
            else:
                make_declaration(source,destination,name,cpf,birth,True,**placement);count=None
            results.append(dict(source=source,destination=str(destination),status='concluido',count=count))
        except Exception as exc:
            results.append(dict(source=source,destination=None,status='erro',error=str(exc)))
    if progress:progress(len(results),len(sources),'Concluído')
    return results
