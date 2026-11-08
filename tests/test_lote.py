"""Testes sem abrir o ERP nem mexer na tela: um dublê faz o papel da janela."""
from pathlib import Path

import pytest

from robo_erp.lote import gravar_resultado, ler_titulos, processar
from robo_erp.tela import ErroDeNegocio, ErroDeTela, escapar_teclas

DADOS = Path(__file__).resolve().parents[1] / "dados" / "titulos_ficticios.csv"


class ErpDuble:
    def __init__(self, falhar_tela_em=None):
        self.lancados, self.saiu, self.proximo = set(), False, 1201
        self.falhar_tela_em = falhar_tela_em

    def entrar(self, usuario, senha):
        assert usuario and senha

    def lancar(self, t):
        if t["documento"] == self.falhar_tela_em:
            raise ErroDeTela("campo sumiu")
        if not t["fornecedor"].endswith(tuple(f"{i:03d}" for i in range(1, 26))):
            raise ErroDeNegocio("Fornecedor não cadastrado.")
        chave = (t["fornecedor"], t["documento"])
        if chave in self.lancados:
            raise ErroDeNegocio("Documento já lançado para este fornecedor.")
        self.lancados.add(chave)
        self.proximo += 1
        return f"{self.proximo - 1:06d}"

    def foto(self, caminho):
        return caminho

    def sair(self):
        self.saiu = True


def test_escapar_teclas():
    assert escapar_teclas("a+b(c)%~") == "a{+}b{(}c{)}{%}{~}"
    assert escapar_teclas("NF 10452") == "NF 10452"


def test_planilha_ficticia(tmp_path):
    erp = ErpDuble()
    linhas = processar(erp, ler_titulos(DADOS), "u", "s", evidencias=tmp_path)
    assert [x["situacao"] for x in linhas] == ["LANÇADO", "LANÇADO", "LANÇADO", "RECUSADO", "RECUSADO", "LANÇADO"]
    assert linhas[3]["motivo"] == "Fornecedor não cadastrado."
    assert linhas[4]["motivo"] == "Documento já lançado para este fornecedor."
    assert erp.saiu


def test_erro_de_tela_vira_erro_com_evidencia_e_sempre_sai(tmp_path):
    erp = ErpDuble(falhar_tela_em="NF 2290")
    linhas = processar(erp, ler_titulos(DADOS), "u", "s", evidencias=tmp_path)
    assert linhas[2]["situacao"] == "ERRO" and "linha_3.png" in linhas[2]["motivo"]
    assert erp.saiu


def test_coluna_faltando(tmp_path):
    arq = tmp_path / "ruim.csv"
    arq.write_text("fornecedor;documento\nX;1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="vencimento"):
        ler_titulos(arq)


def test_resultado_csv(tmp_path):
    linhas = processar(ErpDuble(), ler_titulos(DADOS), "u", "s", evidencias=tmp_path)
    saida = gravar_resultado(linhas, tmp_path / "resultado.csv")
    texto = saida.read_text(encoding="utf-8-sig")
    assert texto.splitlines()[0] == "fornecedor;documento;vencimento;valor;centro;situacao;numero_erp;motivo"
    assert texto.count("LANÇADO") == 4
