"""Provedor de NF-e (SEFAZ) simulado (in-system) (§10.2).

Autoriza a NF-e localmente, gerando uma chave de acesso de 44 dígitos e um XML
no formato aproximado de ``nfeProc``. NF-e sem itens ou com valor <= 0 é
rejeitada, exercitando o fluxo de rejeição.
"""

from __future__ import annotations

import random
from decimal import Decimal
from xml.sax.saxutils import escape

from app.modules.fiscal.adapters.nfe_port import (
    NfeCancelamentoResultado,
    NfeEmissaoResultado,
    NfeItemPayload,
)


def _chave_44() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(44))


class SimuladorSefaz:
    """Implementação simulada de :class:`SefazNfePort`."""

    nome = "simulador"

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
        itens = itens or []
        if not itens or valor_total <= Decimal("0"):
            motivo = "NF-e deve conter ao menos um item com valor maior que zero."
            return NfeEmissaoResultado(
                autorizada=False,
                chave_acesso=None,
                protocolo=None,
                xml=(
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    f"<retNFe><cStat>rejeitada</cStat><xMotivo>{escape(motivo)}</xMotivo>"
                    f"<numero>{escape(numero)}</numero></retNFe>"
                ),
                rejeicao_motivo=motivo,
            )
        chave = _chave_44()
        protocolo = "".join(str(random.randint(0, 9)) for _ in range(15))
        det = ""
        for i, item in enumerate(itens, start=1):
            det += (
                f'<det nItem="{i}"><prod>'
                f"<xProd>{escape(item.descricao)}</xProd>"
                f"<NCM>{escape(item.ncm or '')}</NCM>"
                f"<CFOP>{escape(item.cfop or '')}</CFOP>"
                f"<qCom>{item.quantidade}</qCom>"
                f"<vProd>{item.valor_total}</vProd>"
                "</prod></det>"
            )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<nfeProc versao="4.00"><NFe><infNFe Id="NFe' + chave + '">'
            "<ide>"
            f"<nNF>{escape(numero)}</nNF><serie>{escape(serie)}</serie>"
            f"<natOp>{escape(natureza_operacao)}</natOp>"
            "</ide>"
            f"<emit><CNPJ>{escape(cnpj_emitente)}</CNPJ></emit>"
            "<dest>"
            f"<xNome>{escape(destinatario_nome)}</xNome>"
            f"<doc>{escape(destinatario_doc or '')}</doc>"
            "</dest>"
            f"{det}"
            f"<total><ICMSTot><vNF>{valor_total}</vNF></ICMSTot></total>"
            "</infNFe></NFe>"
            f"<protNFe><infProt><chNFe>{chave}</chNFe>"
            f"<nProt>{protocolo}</nProt><cStat>100</cStat>"
            "<xMotivo>Autorizado o uso da NF-e</xMotivo></infProt></protNFe>"
            "</nfeProc>"
        )
        return NfeEmissaoResultado(
            autorizada=True,
            chave_acesso=chave,
            protocolo=protocolo,
            xml=xml,
        )

    def consultar(self, *, chave_acesso: str) -> str:
        return "autorizada_sefaz"

    def cancelar(self, *, chave_acesso: str, motivo: str) -> NfeCancelamentoResultado:
        protocolo = "".join(str(random.randint(0, 9)) for _ in range(15))
        return NfeCancelamentoResultado(confirmado=True, protocolo=protocolo, motivo=motivo)
