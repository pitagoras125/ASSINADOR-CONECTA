"""Selo criptográfico local de integridade, sem autenticar a identidade declarada.
Certificado técnico autoassinado efêmero: nunca atribuído ao titular do CPF.
"""
from pathlib import Path
import tempfile,secrets

def protect_pdf(source,destination):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from datetime import datetime,timedelta,timezone
    from engine import sign_pdf
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Assinador Conecta - SELO LOCAL - identidade nao verificada')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=3650)).add_extension(x509.BasicConstraints(ca=False,path_length=None),True).add_extension(x509.KeyUsage(True,False,False,False,False,False,False,None,None),True).sign(key,hashes.SHA256()))
    with tempfile.TemporaryDirectory(prefix='conecta-selo-') as folder:
        pfx=Path(folder)/'selo.pfx';password=secrets.token_urlsafe(32)
        pfx.write_bytes(pkcs12.serialize_key_and_certificates(b'Selo tecnico local',key,cert,None,serialization.BestAvailableEncryption(password.encode())))
        pfx.chmod(0o600)
        return sign_pdf(source,destination,pfx,password,reason='Selo técnico local de integridade. CPF declarado; identidade não autenticada. Não ICP-Brasil.',visible=False)

def make_protected_declaration(source,destination,*args,**kwargs):
    from declaration import make_declaration
    from engine import inspect_pdf
    from cpf_evidence import detached_receipt
    destination=Path(destination)
    if destination.exists() or Path(source).resolve()==destination.resolve():raise ValueError('Escolha um novo arquivo de saída.')
    with tempfile.TemporaryDirectory(prefix='conecta-cpf-') as folder:
        draft=Path(folder)/'declaracao.pdf'
        if inspect_pdf(source):
            names=['name','cpf','birth'];data=dict(zip(names,args[:3]));data.update({k:v for k,v in kwargs.items() if k in names})
            detached_receipt(source,draft,**data)
        else:make_declaration(source,draft,*args,**kwargs)
        return protect_pdf(draft,destination)
