"""Utilitários de certificado A1 para assinatura de XML fiscal (§10 + §14.1)."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12


@dataclass(slots=True)
class CertBundle:
    """Pacote descriptografado do certificado A1 do tenant."""

    pfx_bytes: bytes
    password: str
    subject: str


def load_key_cert(bundle: CertBundle):
    """Carrega chave privada e certificado X.509 do PFX."""
    key, cert, _ = pkcs12.load_key_and_certificates(
        bundle.pfx_bytes, bundle.password.encode()
    )
    if key is None or cert is None:
        raise ValueError("PFX sem chave privada ou certificado.")
    return key, cert


def assinar_xml(xml: str, bundle: CertBundle) -> str:
    """Assina o XML com a chave A1 (XML-DSIG simplificado para armazenamento local).

    Em produção com SEFAZ/prefeitura real, o webservice valida a assinatura ICP-Brasil.
    Aqui garantimos que o certificado cadastrado em §14.1 é efetivamente utilizado.
    """
    key, cert = load_key_cert(bundle)
    digest = hashlib.sha256(xml.encode("utf-8")).hexdigest()
    signature = key.sign(
        xml.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    sig_b64 = base64.b64encode(signature).decode()
    subject = cert.subject.rfc4514_string()
    ts = datetime.now(tz=UTC).isoformat()
    return (
        f"{xml}\n"
        f'<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
        f"<ds:SignedInfo><ds:DigestValue>{digest}</ds:DigestValue></ds:SignedInfo>"
        f"<ds:SignatureValue>{sig_b64}</ds:SignatureValue>"
        f"<ds:X509Subject>{subject}</ds:X509Subject>"
        f"<ds:SigningTime>{ts}</ds:SigningTime>"
        f"</ds:Signature>"
    )
