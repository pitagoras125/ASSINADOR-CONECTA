"""Ponte para o repositório pessoal CurrentUser do Windows, sem exportar chaves."""
import base64
import json
import os
import subprocess
from asn1crypto import x509, algos
from pyhanko.sign.signers import Signer
from pyhanko_certvalidator.registry import SimpleCertificateStore

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
try {
 $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
 $store = New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')
 $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
 try {
  if ($request.action -eq 'list') {
   $items = @()
   foreach ($cert in $store.Certificates) {
    if (!$cert.HasPrivateKey -or $cert.NotAfter -lt (Get-Date) -or $cert.NotBefore -gt (Get-Date)) {continue}
    if ($cert.PublicKey.Oid.Value -ne '1.2.840.113549.1.1.1') {continue}
    $usage = $cert.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.15'} | Select-Object -First 1
    if (!$usage -or (([int]$usage.KeyUsages -band 128) -eq 0)) {continue}
    $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    try {
     $chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
     $chain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(1)
     $null = $chain.Build($cert)
     $ders = @($chain.ChainElements | ForEach-Object {[Convert]::ToBase64String($_.Certificate.RawData)})
    } finally {$chain.Dispose()}
    $items += @{chain=$ders;thumbprint=$cert.Thumbprint;name=$cert.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false);expires=$cert.NotAfter.ToString('yyyy-MM-dd');der=[Convert]::ToBase64String($cert.RawData)}
   }
   @{items=@($items)} | ConvertTo-Json -Depth 5 -Compress
  } elseif ($request.action -eq 'sign') {
   $cert = $store.Certificates | Where-Object {$_.Thumbprint -eq $request.thumbprint} | Select-Object -First 1
   if (!$cert -or !$cert.HasPrivateKey) {throw 'Certificado ou chave privada indisponivel para este usuario.'}
   if ($cert.NotAfter -lt (Get-Date) -or $cert.NotBefore -gt (Get-Date)) {throw 'Certificado fora da validade.'}
   $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert)
   if (!$rsa) {throw 'Chave RSA indisponivel.'}
   try {
    $data = [Convert]::FromBase64String($request.data)
    $signed = $rsa.SignData($data,[System.Security.Cryptography.HashAlgorithmName]::SHA256,[System.Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    try {
     $chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
     $chain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(1)
     $null = $chain.Build($cert)
     $ders = @($chain.ChainElements | ForEach-Object {[Convert]::ToBase64String($_.Certificate.RawData)})
    } finally {$chain.Dispose()}
    @{signature=[Convert]::ToBase64String($signed);chain=$ders} | ConvertTo-Json -Depth 5 -Compress
   } finally {$rsa.Dispose()}
  } else {throw 'Operacao desconhecida.'}
 } finally {$store.Close()}
} catch {
 @{error=$_.Exception.Message} | ConvertTo-Json -Compress
 exit 1
}
'''

def call_windows(payload):
    if os.name != 'nt':
        raise RuntimeError('Certificados instalados estão disponíveis apenas no Windows.')
    # Script fixo; dados via stdin JSON, nunca concatenados como código.
    command = base64.b64encode(SCRIPT.encode('utf-16-le')).decode('ascii')
    exe = os.path.join(os.environ.get('SystemRoot',r'C:\Windows'),'System32','WindowsPowerShell','v1.0','powershell.exe')
    try:
        result = subprocess.run([exe,'-NoLogo','-NoProfile','-NonInteractive','-EncodedCommand',command],
            input=json.dumps(payload),capture_output=True,encoding='utf-8',timeout=180,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired:
        raise RuntimeError('O Windows não respondeu a tempo. Verifique a autorização da chave.') from None
    try: response=json.loads(result.stdout.lstrip('\ufeff'))
    except Exception: raise RuntimeError('Não foi possível consultar o Windows. Verifique se o PowerShell está disponível e autorizado.') from None
    if result.returncode or response.get('error'):
        raise RuntimeError(response.get('error','Falha no acesso ao certificado Windows.'))
    return response


def list_certificates():
    return call_windows({'action':'list'})['items']

class WindowsSigner(Signer):
    def __init__(self,item):
        self.item=item
        cert=x509.Certificate.load(base64.b64decode(item['der']))
        registry=SimpleCertificateStore()
        for der in item.get("chain",[]):
            registry.register(x509.Certificate.load(base64.b64decode(der)))
        super().__init__(signing_cert=cert,cert_registry=registry,
            signature_mechanism=algos.SignedDigestAlgorithm({'algorithm':'sha256_rsa'}))
    async def async_sign_raw(self,data,digest_algorithm,dry_run=False):
        if digest_algorithm!='sha256':raise ValueError('Somente SHA-256 é suportado.')
        bits=self.signing_cert.public_key.bit_size
        if dry_run:return bytes((bits+7)//8)
        response=call_windows({'action':'sign','thumbprint':self.item['thumbprint'],
                               'data':base64.b64encode(data).decode('ascii')})
        for der in response.get('chain',[]):
            self.cert_registry.register(x509.Certificate.load(base64.b64decode(der)))
        return base64.b64decode(response['signature'])
