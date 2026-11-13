"""Assinatura incremental. Não armazena senhas nem declara confiança ICP automaticamente."""
from pathlib import Path
from datetime import datetime, timezone
import io
import os
import tempfile
import uuid
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers, fields
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext


def inspect_pdf(path, roots=None):
    """Integridade matemática separada da confiança. Sem consulta OCSP/CRL."""
    results = []
    with open(path, 'rb') as stream:
        reader = PdfFileReader(stream)
        if reader.encrypted:
            raise ValueError('PDF protegido por senha não é suportado nesta versão.')
        for sig in reader.embedded_signatures:
            try:
                context = ValidationContext(trust_roots=roots or [], allow_fetching=False,
                                            revocation_mode='soft-fail')
                status = validate_pdf_signature(sig, signer_validation_context=context)
                results.append(dict(field=sig.field_name,
                    signer=sig.signer_cert.subject.human_friendly,
                    intact=bool(status.intact), valid=bool(status.valid),
                    trusted=bool(status.trusted), coverage=str(status.coverage),
                    modification=str(status.modification_level),
                    allowed=bool(status.docmdp_ok),
                    warning='Revogação não consultada; confiança ICP-Brasil não certificada pelo aplicativo.'))
            except Exception as exc:
                results.append(dict(field=sig.field_name, error=type(exc).__name__))
    return results


def sign_pdf(source, destination, pfx_path=None, password='', reason='Assinatura de documento', *, windows_cert=None, visible=True, page_index=None, box=None, pages=None, rubrics=False, rubric=False):
    if pages is not None:
        if not visible:raise ValueError('A repetição exige chancela visível.')
        from repetition import repeat
        return repeat(sign_pdf,source,destination,page_index=page_index,box=box,pages=pages,rubrics=rubrics,kwargs=dict(pfx_path=pfx_path,password=password,reason=reason,windows_cert=windows_cert,visible=True))
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Escolha um arquivo de saída diferente do original.')
    if destination.exists():
        raise ValueError('O arquivo de saída já existe. Escolha outro nome.')
    if windows_cert is not None:
        from windows_store import WindowsSigner
        signer = WindowsSigner(windows_cert)
        cert = x509.load_der_x509_certificate(signer.signing_cert.dump())
    else:
        raw = Path(pfx_path).read_bytes()
        secret = password.encode('utf-8')
        try:
            key, cert, chain = pkcs12.load_key_and_certificates(raw, secret or None)
        except Exception:
            raise ValueError('Não foi possível abrir o certificado. Verifique o PFX e a senha.') from None
        if key is None or cert is None:
            raise ValueError('O PFX precisa conter o certificado e sua chave privada.')
        signer = signers.SimpleSigner.load_pkcs12_data(raw, other_certs=[], passphrase=secret or None)
    now = datetime.now(timezone.utc)
    if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
        raise ValueError('Certificado vencido ou ainda fora do período de validade.')
    try:
        usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
        if not usage.digital_signature:
            raise ValueError('O certificado não permite assinatura digital.')
    except x509.ExtensionNotFound:
        raise ValueError('Certificado sem extensão de uso de chave.') from None
    before = inspect_pdf(source)
    for result in before:
        if result.get('error') or not result.get('intact') or not result.get('valid') or not result.get('allowed'):
            raise ValueError('O documento contém assinatura inválida ou alterações não permitidas.')
    if signer is None:
        raise ValueError('Falha ao carregar o certificado para assinatura.')
    field_name = 'Conecta_' + uuid.uuid4().hex
    with open(source, 'rb') as stream:
        writer = IncrementalPdfFileWriter(stream)
        if writer.prev.encrypted:
            raise ValueError('PDF protegido por senha não suportado.')
        if visible:
            from placement import choose_placement
            page_index,box=choose_placement(source,page_index,box)
        elif page_index is None:
            page_index=int(writer.root['/Pages']['/Count'])-1
        from seal import seal_pdf,UnifiedStampStyle
        import hashlib,re
        common=cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        name=common[0].value if common else cert.subject.rfc4514_string()
        identifiers=re.findall(r'(?<!\d)(?:\d{14}|\d{11})(?!\d)',name)
        identifier=identifiers[-1] if identifiers else cert.serial_number.__format__('X')
        issuer=cert.issuer.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        issuer=issuer[0].value if issuer else cert.issuer.rfc4514_string()
        from pypdf import PdfReader
        from placement import geometry
        rotation=geometry(PdfReader(str(source)).pages[page_index])['rotation'] if visible else 0
        stamp=UnifiedStampStyle(rotation=rotation,pdf_bytes=seal_pdf(name,identifier,'cert',
            'PROT-'+uuid.uuid4().hex[:20].upper(),hashlib.sha256(source.read_bytes()).hexdigest(),issuer,rubric=rubric))
        metadata = signers.PdfSignatureMetadata(field_name=field_name,
            md_algorithm='sha256', subfilter=fields.SigSeedSubFilter.PADES,
            reason=reason, signer_key_usage={'digital_signature'})
        output = io.BytesIO()
        signers.PdfSigner(metadata, signer=signer,
            stamp_style=stamp, new_field_spec=fields.SigFieldSpec(sig_field_name=field_name, on_page=page_index, box=box if visible else None)).sign_pdf(writer, output=output)
    # Verifica o resultado temporário antes de publicar a saída.
    fd, temp_path = tempfile.mkstemp(prefix='.conecta-', suffix='.pdf', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as temp:
            temp.write(output.getvalue())
        checked = inspect_pdf(temp_path)
        if len(checked) != len(before) + 1 or any(r.get('error') or not r.get('intact') or not r.get('valid') or not r.get('allowed') for r in checked):
            raise ValueError('A verificação das assinaturas falhou. O original foi preservado.')
        # Exclusão mútua impede sobrescrever um arquivo criado durante a operação.
        with open(destination, 'xb') as final:
            try:
                final.write(output.getvalue())
            except Exception:
                final.close()
                destination.unlink(missing_ok=True)
                raise
    finally:
        Path(temp_path).unlink(missing_ok=True)
    return checked
