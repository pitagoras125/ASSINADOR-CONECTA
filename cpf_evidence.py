"""Comprovante local: preserva bytes de PDFs já assinados. Não autentica identidade."""
from pathlib import Path
import hashlib, json, uuid
from datetime import datetime, timezone
from declaration import validate_cpf

def detached_receipt(source,destination,name,cpf,birth):
    from datetime import date
    if len(name.strip().split())<2:raise ValueError('Informe o nome completo.')
    cpf=validate_cpf(cpf)
    try: birthday=datetime.strptime(birth,'%d/%m/%Y').date()
    except ValueError:raise ValueError('Data inválida. Use DD/MM/AAAA.') from None
    if birthday>date.today() or birthday.year<1900:raise ValueError('Data de nascimento inválida.')
    source,destination=Path(source),Path(destination)
    if destination.exists() or source.resolve()==destination.resolve():raise ValueError('Escolha um novo arquivo para o comprovante.')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from xml.sax.saxutils import escape
    styles=getSampleStyleSheet();story=[]
    for title,text in [('Comprovante de manifestação por CPF','Assinador Conecta'),('Dados declarados',name+' — CPF '+cpf),('Documento vinculado',source.name),('SHA-256 do documento original',digest),('Registro local',datetime.now(timezone.utc).isoformat()),('Protocolo',str(uuid.uuid4())),('Limites da comprovação','O arquivo original permanece inalterado. Nome e CPF foram informados pelo usuário. Este comprovante não autentica a identidade, não é assinatura ICP-Brasil e não contém carimbo de tempo confiável. O selo técnico local aplicado ao comprovante detecta alterações após sua geração; não comprova a identidade declarada. O hash permite comparar o arquivo com esta referência, mas não impede a substituição conjunta do comprovante e do arquivo.')]:
        story.extend([Paragraph(escape(title),styles['Heading2']),Paragraph(escape(text),styles['BodyText']),Spacer(1,10)])
    import io
    output=io.BytesIO();SimpleDocTemplate(output).build(story)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('O arquivo mudou durante a operação.')
    with destination.open('xb') as f:f.write(output.getvalue())
    return digest
