"""Provedor NF-e com assinatura por certificado A1 (§10.2 + §14.1)."""

from __future__ import annotations

from decimal import Decimal

from app.modules.fiscal.adapters.certificado import CertBundle, assinar_xml
from app.modules.fiscal.adapters.nfe_port import (
    NfeCancelamentoResultado,
    NfeEmissaoResultado,
    NfeItemPayload,
)
from app.modules.fiscal.adapters.simulador_nfe import SimuladorSefaz


class CertificadoSefaz:
    """Emite via simulador local e assina XML com certificado A1 do tenant."""

    nome = "certificado_a1"

    def __init__(self, cert: CertBundle) -> None:
        self._cert = cert
        self._inner = SimuladorSefaz()

    def emitir(
        self,
        *,
        numero: str,
        serie: str,
        cnpj_emitente: str,
        destinatario_nome: str,
        destinatario_doc: str | None,
        natureza_operacao: str,
        valor_total: Decimal,
        itens: list[NfeItemPayload] | None = None,
    ) -> NfeEmissaoResultado:
        resultado = self._inner.emitir(
            numero=numero,
            serie=serie,
            cnpj_emitente=cnpj_emitente,
            destinatario_nome=destinatario_nome,
            destinatario_doc=destinatario_doc,
            natureza_operacao=natureza_operacao,
            valor_total=valor_total,
            itens=itens,
        )
        if resultado.autorizada and resultado.xml:
            resultado.xml = assinar_xml(resultado.xml, self._cert)
        return resultado

    def consultar(self, *, chave_acesso: str) -> str:
        return self._inner.consultar(chave_acesso=chave_acesso)

    def cancelar(self, *, chave_acesso: str, motivo: str) -> NfeCancelamentoResultado:
        return self._inner.cancelar(chave_acesso=chave_acesso, motivo=motivo)
