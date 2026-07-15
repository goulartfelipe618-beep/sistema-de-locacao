"""Porta (Protocol) do provedor de NF-e / SEFAZ (§10.2).

Contrato para autorização/cancelamento de NF-e junto à SEFAZ. A implementação
real (certificado A1 + webservice SEFAZ) pode ser plugada depois; hoje usamos
:class:`SimuladorSefaz`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class NfeItemPayload:
    descricao: str
    quantidade: Decimal
    valor_total: Decimal
    ncm: str | None = None
    cfop: str | None = None


@dataclass(slots=True)
class NfeEmissaoResultado:
    """Resultado da autorização junto à SEFAZ."""

    autorizada: bool
    chave_acesso: str | None
    protocolo: str | None
    xml: str
    rejeicao_motivo: str | None = None


@dataclass(slots=True)
class NfeCancelamentoResultado:
    """Resultado do cancelamento junto à SEFAZ."""

    confirmado: bool
    protocolo: str | None
    motivo: str | None = None


@runtime_checkable
class SefazNfePort(Protocol):
    """Contrato do provedor de NF-e (SEFAZ)."""

    nome: str

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
        """Autoriza a NF-e na SEFAZ e retorna chave de 44 dígitos/protocolo/XML."""
        ...

    def consultar(self, *, chave_acesso: str) -> str:
        """Consulta a situação de uma NF-e pela chave de acesso."""
        ...

    def cancelar(self, *, chave_acesso: str, motivo: str) -> NfeCancelamentoResultado:
        """Solicita o cancelamento da NF-e junto à SEFAZ."""
        ...
