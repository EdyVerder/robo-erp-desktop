"""Processa uma planilha (CSV) de títulos no ERP e devolve o resultado linha a linha. Não sabe nada de tela:
recebe qualquer objeto com entrar, lancar, foto e sair (nos testes, um dublê)."""
import csv
import logging
from pathlib import Path

from .tela import ErroDeNegocio, ErroDeTela

log = logging.getLogger("robo_erp")
CAMPOS = ["fornecedor", "documento", "vencimento", "valor", "centro"]


def ler_titulos(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    faltando = [c for c in CAMPOS if linhas and c not in linhas[0]]
    if faltando:
        raise ValueError(f"colunas faltando no arquivo: {', '.join(faltando)}")
    return linhas


def processar(erp, titulos, usuario, senha, evidencias=Path("saida/evidencias")):
    resultado = []
    erp.entrar(usuario, senha)
    try:
        for i, t in enumerate(titulos, start=1):
            linha = dict(t)
            try:
                linha["numero_erp"] = erp.lancar(t)
                linha["situacao"], linha["motivo"] = "LANÇADO", ""
                log.info("%d/%d %s %s: título %s", i, len(titulos), t["fornecedor"], t["documento"],
                         linha["numero_erp"])
            except ErroDeNegocio as e:
                linha.update(numero_erp="", situacao="RECUSADO", motivo=str(e))
                log.warning("%d/%d %s %s: recusado, %s", i, len(titulos), t["fornecedor"], t["documento"], e)
            except ErroDeTela as e:
                foto = erp.foto(evidencias / f"linha_{i}.png")
                linha.update(numero_erp="", situacao="ERRO", motivo=f"{e} (evidência: {foto.name})")
                log.error("%d/%d tela não respondeu: %s", i, len(titulos), e)
            resultado.append(linha)
    finally:
        erp.sair()
    return resultado


def gravar_resultado(linhas, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS + ["situacao", "numero_erp", "motivo"], delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    return caminho
