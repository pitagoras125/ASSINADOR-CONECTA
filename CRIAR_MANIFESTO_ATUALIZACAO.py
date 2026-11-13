"""Operação de lançamento: a chave privada fica fora do projeto/repositório."""
import argparse,base64,hashlib,json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from desktop_updates import canonical,ASSET_PREFIX
p=argparse.ArgumentParser();p.add_argument('installer');p.add_argument('--key',required=True);p.add_argument('--version',required=True);p.add_argument('--url',required=True);p.add_argument('--out',default='desktop-update.json');a=p.parse_args()
assert a.url.startswith(ASSET_PREFIX) and a.url.endswith('.exe')
f=Path(a.installer);key=serialization.load_pem_private_key(Path(a.key).read_bytes(),None)
payload=dict(terms_sha256=hashlib.sha256(Path(__file__).with_name('TERMOS.txt').read_bytes()).hexdigest(),app='conecta-pdf-windows',version=a.version,url=a.url,size=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest())
envelope=dict(payload=payload,signature=base64.b64encode(key.sign(canonical(payload))).decode())
Path(a.out).write_text(json.dumps(envelope,ensure_ascii=False,indent=2),encoding='utf-8');print('Manifesto assinado criado.')
