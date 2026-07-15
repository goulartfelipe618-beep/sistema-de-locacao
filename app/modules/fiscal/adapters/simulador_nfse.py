"""Provedor de NFS-e simulado (in-system) (§10.1).

Autoriza a nota no próprio sistema (sem rede), gerando chave de acesso,
protocolo e um XML no formato aproximado de uma NFS-e. Notas com valor de
serviço <= 0 são rejeitadas, exercitando o fluxo de rejeição.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from xml.sax.saxutils import escape

from app.modules.fiscal.adapters.nfse_port import (
    NfseCancelamentoResultado,
    NfseEmissaoResultado,
)


class SimuladorNfse:
    """Implementação simulada de :class:`NfseProvedorPort`."""

    nome = "simulador"

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
        if valor_servico <= Decimal("0"):
            return NfseEmissaoResultado(
                autorizada=False,
                chave_acesso=None,
                protocolo=None,
                xml=self._xml_rejeicao(numero, serie, "Valor do serviço deve ser maior que zero."),
                rejeicao_motivo="Valor do serviço deve ser maior que zero.",
            )
        chave = uuid.uuid4().hex + uuid.uuid4().hex[:12]  # 44 chars
        protocolo = "NFSE" + uuid.uuid4().hex[:16].upper()
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<CompNfse><Nfse><InfNfse>"
            f"<Numero>{escape(numero)}</Numero>"
            f"<Serie>{escape(serie)}</Serie>"
            f"<CodigoVerificacao>{chave}</CodigoVerificacao>"
            f"<Protocolo>{protocolo}</Protocolo>"
            f"<MunicipioIncidencia>{escape(municipio_ibge or '')}</MunicipioIncidencia>"
            "<PrestadorServico>"
            f"<Cnpj>{escape(cnpj_prestador)}</Cnpj>"
            "</PrestadorServico>"
            "<TomadorServico>"
            f"<RazaoSocial>{escape(tomador_nome)}</RazaoSocial>"
            "</TomadorServico>"
            "<Servico>"
            f"<ValorServicos>{valor_servico}</ValorServicos>"
            f"<Aliquota>{aliquota_iss}</Aliquota>"
            f"<ValorIss>{valor_iss}</ValorIss>"
            f"<Discriminacao>{escape(discriminacao)}</Discriminacao>"
            "</Servico>"
            "</InfNfse></Nfse></CompNfse>"
        )
        return NfseEmissaoResultado(
            autorizada=True,
            chave_acesso=chave,
            protocolo=protocolo,
            xml=xml,
        )

    @staticmethod
    def _xml_rejeicao(numero: str, serie: str, motivo: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<CompNfse><Rejeicao>"
            f"<Numero>{escape(numero)}</Numero>"
            f"<Serie>{escape(serie)}</Serie>"
            f"<Motivo>{escape(motivo)}</Motivo>"
            "</Rejeicao></CompNfse>"
        )

    def consultar(self, *, protocolo: str) -> str:
        return "autorizada"

    def cancelar(self, *, chave_acesso: str, motivo: str) -> NfseCancelamentoResultado:
        protocolo = "CANC" + uuid.uuid4().hex[:16].upper()
        return NfseCancelamentoResultado(confirmado=True, protocolo=protocolo, motivo=motivo)
