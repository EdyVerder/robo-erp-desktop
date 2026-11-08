"""Lança no ERP de demonstração os títulos de um CSV e grava o resultado de cada linha.

Uso: python -m robo_erp [dados/titulos_ficticios.csv] [--teclado]
As credenciais vêm de ERP_USUARIO e ERP_SENHA (os padrões só valem para o ERP de demonstração).
"""
import argparse
import logging
import os
from pathlib import Path

from .lote import gravar_resultado, ler_titulos, processar
from .tela import ErpDemo


def main():
    if os.name == "nt":
        os.system("")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivo", nargs="?", default="dados/titulos_ficticios.csv")
    ap.add_argument("--teclado", action="store_true",
                    help="digita tecla por tecla (precisa da janela em primeiro plano; sem isto, roda até minimizado)")
    ap.add_argument("--pasta", default="saida")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="\033[90m%(asctime)s\033[0m %(message)s", datefmt="%H:%M:%S")

    pasta = Path(args.pasta)
    erp = ErpDemo(teclado=args.teclado).abrir()
    linhas = processar(erp, ler_titulos(args.arquivo), os.environ.get("ERP_USUARIO", "demo.usuario"),
                       os.environ.get("ERP_SENHA", "demo-2026"), evidencias=pasta / "evidencias")
    saida = gravar_resultado(linhas, pasta / "resultado.csv")
    lancados = sum(1 for x in linhas if x["situacao"] == "LANÇADO")
    print(f"\n\033[1m{lancados} lançados · {len(linhas) - lancados} para revisar\033[0m · {saida.as_posix()}")


if __name__ == "__main__":
    main()
