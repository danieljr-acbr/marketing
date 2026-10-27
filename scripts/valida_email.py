"""Valida um template de e-mail HTML antes de subir para o RD Station.

Uso:
    python scripts/valida_email.py caminho/email.html [--fix]

Detecta sozinho se o arquivo é uma PÁGINA COMPLETA (importação por URL
do RD, com <html>/<head>/<body>) ou um BLOCO (fragmento para colar num
bloco de HTML/código dentro de um template do RD) e aplica o
checklist certo para cada caso — veja a skill rd-email-import para o
checklist completo e o porquê de cada regra.

Verifica sempre:
  - estrutura HTML (tags de tabela, td, a e p abertas/fechadas)
  - imagens: HTTP 200, formato real (bytes) x extensão, WebP disfarçado de .png/.jpg
    (o site diadoacbr.com.br entrega WebP e o Gmail perde a transparência)
  - imagens sem alt/width, imagens em data: URI (bloqueadas no Gmail)
  - links quebrados e links sem https
  - tamanho do HTML (Gmail corta acima de ~102 KB)

Só em página completa:
  - meta color-scheme (evita logos invertidos no modo escuro)
  - largura do card em %/auto no lugar de px fixo (a importação por URL
    do RD mede a página numa viewport estreita e trava essa largura)

Só em bloco:
  - <html>/<head>/<body>/viewport sobrando (não fazem sentido num
    fragmento — o template do RD já fornece isso)
  - <center>/align="center" ausente (sem o wrapper de página, o card
    alinha à esquerda em vez de centralizado)
  - borda/border-radius no card externo (deve se fundir ao fundo do
    template do RD, não aparecer como um cartão à parte)
  - padding lateral grande (o bloco deve aproveitar quase toda a
    largura disponível, ao contrário de uma página completa)

Com --fix, as imagens WebP são convertidas para PNG em
<pasta do e-mail>/img/<nome do e-mail>/ e o src passa a apontar para o
raw.githubusercontent.com (requer Pillow: python -m pip install pillow).
"""
import io
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

RAW_BASE = "https://raw.githubusercontent.com/danieljr-acbr/marketing/main/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
CHECK_TAGS = {"table", "tr", "td", "a", "p", "div", "span", "h1", "h2", "h3", "ul", "li", "strong"}
VOID = {"img", "br", "meta", "hr", "link", "input"}


class Estrutura(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.erros, self.imgs, self.links = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img":
            self.imgs.append((self.getpos()[0], a))
        if tag == "a" and a.get("href"):
            self.links.append((self.getpos()[0], a["href"]))
        if tag in CHECK_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag not in CHECK_TAGS:
            return
        if not self.stack or self.stack[-1][0] != tag:
            abertos = [t for t, _ in self.stack[-3:]]
            self.erros.append(f"linha {self.getpos()[0]}: </{tag}> inesperado (abertos: {abertos})")
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break
            return
        self.stack.pop()


def baixa(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()


def formato(data):
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpeg"
    if data.startswith(b"GIF8"):
        return "gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    return "desconhecido"


PAD_RE = re.compile(r"padding\s*:\s*(-?\d+)px(?:\s+(-?\d+)px)?(?:\s+(-?\d+)px)?(?:\s+(-?\d+)px)?", re.I)


def padding_lateral(declaracao):
    """Dado o valor de uma propriedade CSS padding (shorthand), devolve o
    valor lateral (direita/esquerda) em px, seguindo as regras do CSS:
    1 valor -> todos os lados; 2 ou 3 valores -> o 2º é a lateral; 4
    valores -> o 2º (direita) é usado como referência."""
    m = PAD_RE.search("padding:" + declaracao)
    if not m:
        return None
    vals = [int(v) for v in m.groups() if v is not None]
    return vals[1] if len(vals) >= 2 else vals[0]


def achar_tabela_card(sem_comentarios):
    """Acha a tag <table ...> do card do e-mail, não a tabela de fundo
    full-bleed que envolve tudo. Nos templates deste repositório, essa
    tabela de fundo é sempre width=100% sem max-width nem class="card";
    o card em si costuma ter class="card" e/ou max-width no style. Na
    ausência dos dois sinais, assume a 2ª tabela do documento (padrão:
    fundo -> td align=center -> card) — ou a 1ª, se só houver uma
    (como num bloco, que não tem tabela de fundo)."""
    tabelas = re.findall(r"<table\b[^>]*>", sem_comentarios, re.I)
    for t in tabelas:
        if 'class="card"' in t.lower():
            return t
    for t in tabelas:
        if "max-width" in t.lower():
            return t
    if len(tabelas) > 1:
        return tabelas[1]
    return tabelas[0] if tabelas else None


def checa_bloco(html, sem_comentarios, erros, avisos):
    """Checklist específico para um BLOCO (fragmento sem <html>/<head>/<body>,
    pensado para colar num bloco de HTML customizado dentro de um
    template do RD Station, em vez de importar a página inteira)."""
    for tag in ("<html", "<head", "<body", 'name="viewport"'):
        if tag in sem_comentarios.lower():
            erros.append(f"bloco não deveria ter {tag.strip('<').strip()}: o template do RD já fornece isso")

    if "<style" in sem_comentarios.lower():
        avisos.append("bloco com <style>: o RD Station não confia em CSS no <head>/<style> na importação — prefira tudo inline (já é o padrão deste repositório)")

    if "<center" not in sem_comentarios.lower():
        avisos.append('sem <center>: sem o wrapper de página, o card tende a alinhar à esquerda em vez de centralizado no bloco do RD')

    tag_externa = achar_tabela_card(sem_comentarios)
    if tag_externa:
        if 'align="center"' not in tag_externa.lower():
            avisos.append('tabela externa sem align="center": some sem o <center> junto, o card pode alinhar à esquerda')
        sm = re.search(r'style="([^"]*)"', tag_externa, re.I)
        estilo = sm.group(1).lower() if sm else ""
        if "border-radius" in estilo or re.search(r"border\s*:\s*[1-9]", estilo):
            avisos.append("tabela externa do bloco com border/border-radius: o card deve se fundir ao fundo do template do RD, não aparecer como um cartão à parte")

    laterais = []
    for decl in re.findall(r'padding\s*:\s*[^;"]+', sem_comentarios, re.I):
        lat = padding_lateral(decl[len("padding"):].lstrip(": "))
        if lat is not None:
            laterais.append(lat)
    # >24px cobre folgas normais de botões/caixas internas (16-24px) sem
    # soar alarme; só pega o padrão "de página completa" (normalmente 32px)
    # que, num bloco, desperdiça parte da largura disponível.
    grandes = [v for v in laterais if v > 24]
    if grandes:
        avisos.append(f"{len(grandes)} padding(s) lateral(is) acima de 24px (até {max(grandes)}px): num bloco, o texto deve aproveitar quase toda a largura — considere ~12px nas linhas de conteúdo (botões e caixas internas podem ficar com mais folga)")


def checa_pagina_completa(sem_comentarios, erros, avisos):
    """Checklist específico para uma PÁGINA COMPLETA (importada por URL no
    RD Station): aqui a largura precisa ser px fixo, não %/auto — a
    importação por URL do RD parece medir a página numa viewport
    estreita e trava essa largura para todos os dispositivos depois."""
    tag_card = achar_tabela_card(sem_comentarios)
    if tag_card:
        sm = re.search(r'style="([^"]*)"', tag_card, re.I)
        estilo = sm.group(1).lower() if sm else ""
        width_attr = re.search(r'\bwidth\s*=\s*"([^"]*)"', tag_card, re.I)
        usa_percentual = "%" in estilo.split("max-width")[0] if "width" in estilo else False
        usa_percentual = usa_percentual or (width_attr and "%" in width_attr.group(1))
        sem_width_fixo = "width" not in estilo and not (width_attr and width_attr.group(1).strip("%").isdigit() and "%" not in width_attr.group(1))
        if usa_percentual or sem_width_fixo:
            avisos.append("tabela externa sem largura fixa em px (ex.: width=\"600\" + style=\"width:600px\"): em página completa, %/auto pode medir errado na importação por URL do RD e ficar apertada")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fix = "--fix" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    caminho = args[0]
    html = open(caminho, "rb").read().decode("utf-8")
    erros, avisos = [], []

    p = Estrutura()
    p.feed(html)
    erros += p.erros
    erros += [f"linha {l}: <{t}> nunca fechado" for t, l in p.stack]

    kb = len(html.encode("utf-8")) / 1024
    if kb > 102:
        erros.append(f"HTML com {kb:.0f} KB: o Gmail corta a mensagem acima de ~102 KB")

    sem_comentarios = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    is_bloco = "<html" not in sem_comentarios.lower()
    if is_bloco:
        checa_bloco(html, sem_comentarios, erros, avisos)
    else:
        if 'name="color-scheme"' not in html:
            avisos.append('sem <meta name="color-scheme" content="light">: clientes em modo escuro podem inverter cores e logos')
        checa_pagina_completa(sem_comentarios, erros, avisos)

    pasta = os.path.dirname(os.path.abspath(caminho))
    nome = os.path.splitext(os.path.basename(caminho))[0]
    img_dir = os.path.join(pasta, "img", nome)
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    corrigidas = {}

    vistos = set()
    for linha, a in p.imgs:
        src = a.get("src", "")
        if "alt" not in a:
            avisos.append(f"linha {linha}: <img> sem alt ({src[-50:]})")
        if "width" not in a:
            avisos.append(f"linha {linha}: <img> sem atributo width ({src[-50:]})")
        if src.startswith("data:"):
            erros.append(f"linha {linha}: imagem em data: URI, o Gmail bloqueia")
            continue
        if src in vistos:
            continue
        vistos.add(src)
        if not src.startswith("https://"):
            erros.append(f"linha {linha}: imagem sem https: {src}")
            continue
        try:
            status, ctype, data = baixa(src)
        except urllib.error.HTTPError as e:
            erros.append(f"linha {linha}: imagem HTTP {e.code}: {src}")
            continue
        except Exception as e:
            erros.append(f"linha {linha}: imagem inacessível ({e}): {src}")
            continue
        fmt = formato(data)
        ext = os.path.splitext(src.split("?")[0])[1].lower().lstrip(".")
        ext = "jpeg" if ext == "jpg" else ext
        if fmt == "webp":
            erros.append(f"linha {linha}: servida como WebP (Content-Type {ctype}), o Gmail perde a transparência: {src}")
            if fix:
                from PIL import Image
                im = Image.open(io.BytesIO(data)).convert("RGBA")
                if im.width > 300:
                    im.thumbnail((300, 300 * im.height // im.width), Image.LANCZOS)
                os.makedirs(img_dir, exist_ok=True)
                arq = os.path.splitext(os.path.basename(src.split("?")[0]))[0] + ".png"
                im.save(os.path.join(img_dir, arq), "PNG", optimize=True)
                rel = os.path.relpath(os.path.join(img_dir, arq), repo).replace(os.sep, "/")
                corrigidas[src] = RAW_BASE + rel
        elif fmt != ext:
            avisos.append(f"linha {linha}: extensão .{ext} mas o arquivo é {fmt}: {src}")
        if len(data) > 200 * 1024:
            avisos.append(f"linha {linha}: imagem com {len(data) // 1024} KB, considere reduzir: {src}")

    for href, linha in {h: l for l, h in p.links}.items():
        if href.startswith(("mailto:", "tel:", "#")) or "*|" in href or "{{" in href or re.fullmatch(r"%[\w-]+%", href):
            continue
        if not href.startswith("https://"):
            avisos.append(f"linha {linha}: link sem https: {href}")
            continue
        try:
            baixa(href)
        except urllib.error.HTTPError as e:
            erros.append(f"linha {linha}: link HTTP {e.code}: {href}")
        except Exception as e:
            erros.append(f"linha {linha}: link inacessível ({e}): {href}")

    if corrigidas:
        for velho, novo in corrigidas.items():
            html = html.replace(velho, novo)
        open(caminho, "wb").write(html.encode("utf-8"))

    modo = "bloco" if is_bloco else "página completa"
    print(f"{caminho} [{modo}]: {len(p.imgs)} imagens, {len(p.links)} links, {kb:.0f} KB")
    for e in erros:
        print("  ERRO  ", e)
    for a in avisos:
        print("  AVISO ", a)
    if corrigidas:
        print(f"  {len(corrigidas)} imagem(ns) convertida(s) para PNG em {os.path.relpath(img_dir, repo)}; rode de novo após o push para conferir.")
    if not erros and not avisos:
        print("  OK")
    sys.exit(1 if erros and not corrigidas else 0)


if __name__ == "__main__":
    main()
