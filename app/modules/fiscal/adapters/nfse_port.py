"""Porta (Protocol) do provedor de NFS-e (§10.1).

Define o contrato que qualquer provedor municipal deve implementar. A
implementação real (webservice de cada prefeitura) pode ser plugada mais tarde
sem alterar o domínio; hoje usamos :class:`SimuladorNfse`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class NfseEmissaoResultado:
    """Resultado da emissão junto ao provedor municipal."""

    autorizada: bool
    chave_acesso: str | None
    protocolo: str | None
    xml: str
    rejeicao_motivo: str | None = None


@dataclass(slots=True)
class NfseCancelamentoResultado:
    """Resultado do cancelamento junto ao provedor municipal."""

    confirmado: bool
    protocolo: str | None
    motivo: str | None = None


@runtime_checkable
class NfseProvedorPort(Protocol):
    """Contrato do provedor de NFS-e (por município)."""

    nome: str

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
        """Emite a NFS-e no provedor municipal e retorna chave/protocolo/XML."""
        ...

    def consultar(self, *, protocolo: str) -> str:
        """Consulta a situação de uma NFS-e pelo protocolo."""
        ...

    def cancelar(self, *, chave_acesso: str, motivo: str) -> NfseCancelamentoResultado:
        """Solicita o cancelamento da NFS-e junto ao provedor."""
        ...
