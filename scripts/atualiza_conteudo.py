#!/usr/bin/env python3
"""
Atualiza os blocos dinamicos dos templates de newsletter a partir de 3 feeds RSS:
  - Noticias  -> secao "Noticias do ACBr" (forum Invision)
  - Podcast   -> Papo Pro ACBr (RSS do Spotify/hospedagem do podcast)
  - Video     -> canal do YouTube do Projeto ACBr

Substitui o conteudo entre marcadores especificos em cada template:
    <!-- NOTICIAS:INICIO --> ... <!-- NOTICIAS:FIM -->
    <!-- PODCAST:INICIO -->  ... <!-- PODCAST:FIM -->
    <!-- VIDEO:INICIO -->    ... <!-- VIDEO:FIM -->
Nao toca em mais nada. Requisitos: feedparser (instalado pelo workflow).
"""

import os
import re
import glob
import html
import feedparser

# --- CONFIG: URLs dos feeds (preencha ou use as envs no repositorio) ---
FEED_NOTICIAS = os.environ.get("RSS_FEED_NOTICIAS", "")  # vem do Environment secret RSS_FEED_NOTICIAS (nao fixar a chave aqui)
FEED_PODCAST  = os.environ.get("RSS_FEED_PODCAST")  or "https://anchor.fm/s/53cc5990/podcast/rss"
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID") or "UCUK2VZuC1cmJ2qJKVzVnZEg"
FEED_VIDEO    = f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}"

GLOB_NEWSLETTER = "**/novidades-comunidade/**/*.html"
QTD_NOTICIAS = 3

NAVY = "#1f3864"
SECOND = "#5a5f66"


def edicao_mes_atual():
    """Retorna 'dia de mes' em portugues, no fuso de Brasilia. Sem dependencia externa."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        agora = datetime.utcnow()  # fallback; diferenca de fuso so afeta a virada do dia/mes
    meses = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    return f"{agora.day} de {meses[agora.month - 1]}"


def limpa(texto, limite=160):
    txt = re.sub(r"<[^>]+>", "", texto or "")
    txt = html.unescape(txt).strip().replace("\n", " ")
    if limite and len(txt) > limite:
        txt = txt[:limite].rsplit(" ", 1)[0] + "\u2026"
    return txt


def parse(url, nome):
    if "COLE_" in url:
        print(f"AVISO: feed de {nome} nao configurado - bloco mantido.")
        return None
    feed = feedparser.parse(url)
    if not feed.entries:
        print(f"AVISO: feed de {nome} vazio ou inacessivel - bloco mantido.")
        return None
    return feed.entries


def bloco_noticia(item):
    t = html.escape(item.get("title", "Sem titulo"))
    l = html.escape(item.get("link", "#"))
    r = html.escape(limpa(item.get("summary", "")))
    return f"""        <tr><td style="padding:18px 32px 0;" class="px">
          <p style="margin:0 0 4px; font-family:Arial,sans-serif; font-size:17px; font-weight:bold; color:{NAVY};">{t}</p>
          <p style="margin:0 0 6px; font-family:Arial,sans-serif; font-size:15px; line-height:1.6; color:{SECOND};">{r}</p>
          <a href="{l}" style="font-family:Arial,sans-serif; font-size:14px; font-weight:bold; color:{NAVY};">Ler no f&oacute;rum &rarr;</a>
        </td></tr>
        <tr><td style="padding:16px 32px 0;" class="px"><div style="height:1px; background:#eceef1;"></div></td></tr>"""


def bloco_podcast(item):
    t = html.escape(item.get("title", "Novo episodio"))
    l = html.escape(item.get("link", "#"))
    r = html.escape(limpa(item.get("summary", ""), 140))
    return f"""            <p style="margin:0 0 4px; font-family:Arial,sans-serif; font-size:15px; font-weight:bold; color:{NAVY};">&#127908; Papo Pro ACBr: {t}</p>
            <p style="margin:0 0 8px; font-family:Arial,sans-serif; font-size:14px; line-height:1.6; color:{SECOND};">{r}</p>
            <a href="{l}" style="font-family:Arial,sans-serif; font-size:14px; font-weight:bold; color:{NAVY};">Ouvir epis&oacute;dio &rarr;</a>"""


def bloco_video(item):
    t = html.escape(item.get("title", "Novo video"))
    l = html.escape(item.get("link", "#"))
    return f"""            <p style="margin:0 0 6px; font-family:Arial,sans-serif; font-size:15px; font-weight:bold; color:{NAVY};">&#9654;&#65039; No YouTube: {t}</p>
            <a href="{l}" style="font-family:Arial,sans-serif; font-size:14px; font-weight:bold; color:{NAVY};">Assistir &rarr;</a>"""


def substitui_bloco(conteudo, marca, novo_miolo):
    ini = f"<!-- {marca}:INICIO -->"
    fim = f"<!-- {marca}:FIM -->"
    if ini not in conteudo or fim not in conteudo:
        return conteudo, False
    antes = conteudo.split(ini)[0]
    depois = conteudo.split(fim)[1]
    return antes + f"{ini}\n{novo_miolo}\n        {fim}" + depois, True


def substitui_inline(conteudo, marca, novo_valor):
    """Como substitui_bloco, mas sem quebras de linha - para campos dentro de uma unica linha
    (ex.: a data no cabecalho). Os marcadores INICIO/FIM ficam no arquivo para a proxima
    atualizacao poder trocar o valor de novo (o token puro *|...|* desaparece apos o 1o uso)."""
    ini = f"<!-- {marca}:INICIO -->"
    fim = f"<!-- {marca}:FIM -->"
    padrao = re.compile(re.escape(ini) + r".*?" + re.escape(fim), re.DOTALL)
    novo, n = padrao.subn(f"{ini}{novo_valor}{fim}", conteudo)
    return novo, n > 0


def main():
    noticias = parse(FEED_NOTICIAS, "noticias")
    podcast  = parse(FEED_PODCAST, "podcast")
    videos   = parse(FEED_VIDEO, "video") if "COLE_" not in YT_CHANNEL_ID else None

    miolo_noticias = "\n".join(bloco_noticia(i) for i in noticias[:QTD_NOTICIAS]) if noticias else None
    miolo_podcast  = bloco_podcast(podcast[0]) if podcast else None
    miolo_video    = bloco_video(videos[0]) if videos else None

    mes = edicao_mes_atual()
    print(f"Edicao do mes: {mes}")

    arquivos = glob.glob(GLOB_NEWSLETTER, recursive=True)
    if not arquivos:
        print("AVISO: nenhum arquivo de newsletter encontrado no glob.")
        return

    total = 0
    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as f:
            c = f.read()
        original = c
        c, _ = substitui_inline(c, "EDICAO_MES", mes)
        if miolo_noticias:
            c, _ = substitui_bloco(c, "NOTICIAS", miolo_noticias)
        if miolo_podcast:
            c, _ = substitui_bloco(c, "PODCAST", miolo_podcast)
        if miolo_video:
            c, _ = substitui_bloco(c, "VIDEO", miolo_video)
        if c != original:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(c)
            total += 1
            print(f"atualizado: {caminho}")

    fontes = [n for n, v in [("noticias", noticias), ("podcast", podcast), ("video", videos)] if v]
    print(f"\nConcluido. {total} arquivo(s) atualizado(s). Fontes ativas: {', '.join(fontes) or 'nenhuma'}.")


if __name__ == "__main__":
    main()
