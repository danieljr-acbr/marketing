"""Valida um template de e-mail HTML antes de subir para o RD Station.

Uso:
    python scripts/valida_email.py caminho/email.html [--fix]

Verifica:
  - estrutura HTML (tags de tabela, td, a e p abertas/fechadas)
  - imagens: HTTP 200, formato real (bytes) x extensão, WebP disfarçado de .png/.jpg
    (o site diadoacbr.com.br entrega WebP e o Gmail perde a transparência)
  - imagens sem alt/width, imagens em data: URI (bloqueadas no Gmail)
  - links quebrados e links sem https
  - tamanho do HTML (Gmail corta acima de ~102 KB)
  - meta color-scheme (evita logos invertidos no modo escuro)

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
    if 'name="color-scheme"' not in html:
        avisos.append('sem <meta name="color-scheme" content="light">: clientes em modo escuro podem inverter cores e logos')

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
        if href.startswith(("mailto:", "tel:", "#")) or "*|" in href or "{{" in href:
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

    print(f"{caminho}: {len(p.imgs)} imagens, {len(p.links)} links, {kb:.0f} KB")
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
