"""Provedor NFS-e com assinatura por certificado A1 (§10.1 + §14.1)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.fiscal.adapters.certificado import CertBundle, assinar_xml
from app.modules.fiscal.adapters.nfse_port import (
    NfseCancelamentoResultado,
    NfseEmissaoResultado,
)
from app.modules.fiscal.adapters.simulador_nfse import SimuladorNfse


class CertificadoNfse:
    """Emite via simulador local e assina XML com certificado A1 do tenant."""

    nome = "certificado_a1"

    def __init__(self, cert: CertBundle) -> None:
        self._cert = cert
        self._inner = SimuladorNfse()

    def emitir(
        self,
        *,
        numero: str,
        serie: str,
        cnpj_prestador: str,
        tomador_nome: str,
        municipio_ibge: str | None,
        valor_servico: Decimal,
        aliquota_iss: Decimal,
        valor_iss: Decimal,
        discriminacao: str,
    ) -> NfseEmissaoResultado:
        resultado = self._inner.emitir(
            numero=numero,
            serie=serie,
            cnpj_prestador=cnpj_prestador,
            tomador_nome=tomador_nome,
            municipio_ibge=municipio_ibge,
            valor_servico=valor_servico,
            aliquota_iss=aliquota_iss,
            valor_iss=valor_iss,
            discriminacao=discriminacao,
        )
        if resultado.autorizada and resultado.xml:
            resultado.xml = assinar_xml(resultado.xml, self._cert)
        return resultado

    def consultar(self, *, protocolo: str) -> str:
        return self._inner.consultar(protocolo=protocolo)

    def cancelar(self, *, chave_acesso: str, motivo: str) -> NfseCancelamentoResultado:
        return self._inner.cancelar(chave_acesso=chave_acesso, motivo=motivo)
