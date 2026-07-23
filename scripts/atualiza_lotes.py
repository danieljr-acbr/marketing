#!/usr/bin/env python3
"""
Atualiza os valores de lote nos e-mails de VENDA (pasta dia-do-acbr-2026) via de-para
com estado.

Como funciona:
- Le os valores ATUAIS de lote.json (o "de").
- Le os valores NOVOS das variaveis de ambiente (o "para"), informadas ao rodar a Action:
    NOVO_VALOR_ATUAL, NOVO_VALOR_PROXIMO, NOVA_DATA_VIRADA
- Substitui, nos templates de venda, as ocorrencias dos valores atuais pelos novos.
- Usa substituicao em duas fases (com sentinelas) para evitar o efeito cascata
  (ex.: trocar 749->799 e depois 799->849 pegaria os 799 recem-criados).
- Grava os novos valores em lote.json para a proxima virada.

Nao depende de nenhuma biblioteca externa.
"""

import os
import re
import json
import glob

ESTADO = "lote.json"
GLOB_VENDA = "**/dia-do-acbr-2026/**/*.html"

SENT_ATUAL = "@@LOTE_ATUAL@@"
SENT_PROX  = "@@LOTE_PROXIMO@@"
SENT_DATA  = "@@LOTE_DATA@@"


def carrega_estado():
    with open(ESTADO, encoding="utf-8") as f:
        return json.load(f)


def salva_estado(d):
    with open(ESTADO, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")


def regex_preco(valor):
    """
    Casa 'R$' + espaco/nbsp opcional + o valor, preservando variacoes de formatacao.
    Ex.: 'R$ 749', 'R$749', 'R$&nbsp;749'. O grupo 1 mantem o prefixo 'R$ ' original.
    """
    v = re.escape(valor)
    return re.compile(r"(R\$\s*(?:&nbsp;)?\s*)" + v + r"(?!\d)")


def substitui_precos(texto, atual, proximo, data, novo_atual, novo_proximo, nova_data):
    # Fase 1: valores atuais -> sentinelas (evita cascata)
    texto = regex_preco(atual).sub(lambda m: m.group(1) + SENT_ATUAL, texto)
    texto = regex_preco(proximo).sub(lambda m: m.group(1) + SENT_PROX, texto)
    texto = texto.replace(data, SENT_DATA)
    # Fase 2: sentinelas -> valores novos
    texto = texto.replace(SENT_ATUAL, novo_atual)
    texto = texto.replace(SENT_PROX, novo_proximo)
    texto = texto.replace(SENT_DATA, nova_data)
    return texto


def main():
    estado = carrega_estado()
    atual, proximo, data = estado["valor_atual"], estado["valor_proximo"], estado["data_virada"]

    novo_atual   = os.environ.get("NOVO_VALOR_ATUAL", "").strip()
    novo_proximo = os.environ.get("NOVO_VALOR_PROXIMO", "").strip()
    nova_data    = os.environ.get("NOVA_DATA_VIRADA", "").strip()

    if not (novo_atual and novo_proximo and nova_data):
        raise SystemExit("ERRO: informe NOVO_VALOR_ATUAL, NOVO_VALOR_PROXIMO e NOVA_DATA_VIRADA.")

    print(f"De:  atual={atual}  proximo={proximo}  data={data}")
    print(f"Para: atual={novo_atual}  proximo={novo_proximo}  data={nova_data}\n")

    arquivos = glob.glob(GLOB_VENDA, recursive=True)
    if not arquivos:
        print("AVISO: nenhum e-mail de venda encontrado no glob (dia-do-acbr-2026).")
        return

    total = 0
    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as f:
            c = f.read()
        novo = substitui_precos(c, atual, proximo, data, novo_atual, novo_proximo, nova_data)
        if novo != c:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(novo)
            total += 1
            print(f"atualizado: {caminho}")

    if total == 0:
        print("\nNenhuma ocorrencia encontrada. Verifique se os valores em lote.json")
        print("batem EXATAMENTE com o texto dos templates (ex.: 'R$ 749').")
    else:
        salva_estado({"valor_atual": novo_atual,
                      "valor_proximo": novo_proximo,
                      "data_virada": nova_data})
        print(f"\nConcluido. {total} arquivo(s) atualizado(s). lote.json atualizado para a proxima virada.")


if __name__ == "__main__":
    main()
