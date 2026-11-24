"""Canal Windows separado do APK; metadados assinados e hash do instalador."""
import base64,hashlib,json,os,re,subprocess,sys,tempfile
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
VERSION='1.4.2'
MANIFEST_URL='https://github.com/pitagoras125/assinador-conecta-atualizacoes/releases/latest/download/desktop-update.json'
ASSET_PREFIX='https://github.com/pitagoras125/assinador-conecta-atualizacoes/releases/download/'
MAX_DOWNLOAD=600*1024*1024

def canonical(payload):return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def version_tuple(v):
    if not isinstance(v,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',v):raise ValueError('Versão de atualização inválida.')
    return tuple(map(int,v.split('.')))

def validate_manifest(envelope,public_key=None,current=VERSION):
    payload=envelope['payload'];signature=base64.b64decode(envelope['signature'],validate=True)
    key=public_key or bytes.fromhex((Path(__file__).parent/'update_public_key.hex').read_text().strip())
    Ed25519PublicKey.from_public_bytes(key).verify(signature,canonical(payload))
    if payload.get('app')!='conecta-pdf-windows':raise ValueError('Atualização de outro aplicativo.')
    if version_tuple(payload['version'])<=version_tuple(current):return None
    url=payload['url'];path=urlsplit(url)
    if not url.startswith(ASSET_PREFIX) or path.query or path.fragment or not path.path.lower().endswith('.exe'):raise ValueError('Origem de atualização não autorizada.')
    if not re.fullmatch('[0-9a-f]{64}',payload['sha256']):raise ValueError('Hash inválido.')
    if type(payload['size']) is not int or not 0<payload['size']<=MAX_DOWNLOAD:raise ValueError('Tamanho de atualização inválido.')
    return payload

class SecureRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlsplit(newurl)
        if p.scheme!='https' or p.hostname not in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com') or p.username or p.password:raise ValueError('Redirecionamento de atualização não autorizado.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def open_url(url):return build_opener(SecureRedirect()).open(Request(url,headers={'User-Agent':'ConectaPDF/'+VERSION}),timeout=30)

def check_update():
    from urllib.error import HTTPError
    try:
        with open_url(MANIFEST_URL) as response:raw=response.read(65537)
    except HTTPError as exc:
        if exc.code==404:return None
        raise
    if len(raw)>65536:raise ValueError('Manifesto excede o tamanho permitido.')
    return validate_manifest(json.loads(raw))

def download_update(payload):
    # Payload must already have passed signed-manifest validation.
    folder=Path(tempfile.mkdtemp(prefix='conecta-pdf-update-'));target=folder/'ConectaPDF-Setup.exe';digest=hashlib.sha256();total=0
    try:
        with open_url(payload['url']) as response,open(target,'xb') as output:
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>payload['size']:raise ValueError('O download ultrapassou o tamanho autorizado.')
                digest.update(block);output.write(block)
        if total!=payload['size'] or digest.hexdigest()!=payload['sha256']:raise ValueError('A integridade do instalador não foi confirmada.')
        return str(target)
    except Exception:
        target.unlink(missing_ok=True);folder.rmdir();raise

def install_update(path,payload):
    if sys.platform!='win32' or not getattr(sys,'frozen',False):raise ValueError('A instalação automática está disponível no aplicativo Windows instalado.')
    data=Path(path).read_bytes()
    if len(data)!=payload['size'] or hashlib.sha256(data).hexdigest()!=payload['sha256']:raise ValueError('O instalador foi alterado após o download.')
    import winreg
    accepted = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Conecta\PDF\Installer") as key:
            accepted = winreg.QueryValueEx(key, "AcceptedTerms")[0]
    except OSError:
        pass
    args = [str(Path(path).resolve()), '/NORESTART', '/CLOSEAPPLICATIONS']
    terms = payload.get('terms_sha256')
    if isinstance(terms, str) and re.fullmatch('[0-9a-f]{64}', terms) and accepted == terms:
        args.append('/SILENT')
    subprocess.Popen(args, shell=False)
