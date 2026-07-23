# Automacao de conteudo da newsletter (RSS -> GitHub Actions)

Puxa automaticamente **3 fontes** da comunidade e injeta nos templates de newsletter,
com commit automatico. Roda sozinho no GitHub Actions.

| Bloco | Fonte | Feed |
|---|---|---|
| Noticias | Secao "Noticias do ACBr" (forum Invision) | RSS da secao |
| Podcast | Papo Pro ACBr | RSS do podcast (Spotify/hospedagem) |
| Video | Canal do Projeto ACBr no YouTube | RSS nativo do canal |

## Por que nao e o HTML que "puxa" sozinho
E-mail nao executa JavaScript. A montagem acontece **antes do envio**: o GitHub Actions
atualiza os HTML periodicamente e o e-mail sai com a versao mais recente ja embutida.


## JA CONFIGURADO neste pacote

O script `scripts/atualiza_conteudo.py` ja vem com os 3 feeds preenchidos:
- Noticias: feed da secao "Noticias do ACBr" (testado, retornando as noticias reais)
- Podcast:  https://anchor.fm/s/53cc5990/podcast/rss (Papo Pro ACBr)
- YouTube:  channel_id UCUK2VZuC1cmJ2qJKVzVnZEg

Ou seja: da para subir e rodar direto. As variaveis de repositorio (passo 2) sao
opcionais - servem so para trocar os feeds sem editar o script.

### ATENCAO - chave privada no feed de noticias
A URL do feed de noticias contem `member=79334&key=...`. Essa chave e pessoal e
da acesso ao seu feed. Como o repositorio pode ser publico, o RECOMENDADO e:
- NAO deixar a URL com a chave fixa no script de um repo publico.
- Em vez disso, cadastrar a URL completa como variavel de repositorio
  `RSS_FEED_NOTICIAS` (Settings > Secrets and variables > Actions > Variables) e
  remover a chave do script (deixar so o placeholder). O workflow ja le a env.
- Se a secao de noticias tiver um RSS PUBLICO (sem member/key), prefira ele no lugar.


## Arquivos
- `scripts/atualiza_conteudo.py` - le os 3 feeds e injeta noticias, podcast e video.
- `.github/workflows/atualiza-noticias.yml` - agenda (semanal) e faz commit.

## Instalacao (uma vez)

### 1. Descobrir as 3 URLs/IDs

**Noticias (Invision):** entre na secao "Noticias do ACBr", role ate o rodape e clique
no icone RSS (canto inferior esquerdo). Formato tipico:
`https://www.projetoacbr.com.br/forum/forum/35-noticias-do-acbr/?rss=1`

**Podcast (Papo Pro ACBr):** o RSS do podcast e o feed da hospedagem (nao o link do
Spotify em si). Se o podcast e distribuido por Spotify for Podcasters/Anchor, o feed
costuma ser `https://anchor.fm/s/XXXXXXXX/podcast/rss`. Se voce nao tiver o link do RSS,
me avise que eu ajudo a localizar a partir do endereco do programa.

**Video (YouTube):** voce precisa do CHANNEL_ID (string que comeca com "UC").
Como achar: abra o canal do ACBr no YouTube, veja o codigo-fonte da pagina (Ctrl+U) e
procure por `channel_id=` OU por `"externalId":"UC..."`. Copie o valor "UC...".
O script monta a URL do feed sozinho.

### 2. Cadastrar no repositorio
GitHub: **Settings -> Secrets and variables -> Actions -> aba Variables -> New variable**,
criando as tres:
- `RSS_FEED_NOTICIAS` = (URL do RSS de noticias)
- `RSS_FEED_PODCAST`  = (URL do RSS do podcast)
- `YT_CHANNEL_ID`     = (o "UC..." do canal)

Configurou so uma ou duas? Sem problema: as fontes nao preenchidas sao ignoradas e os
blocos correspondentes ficam como estao. Da para ativar aos poucos.

### 3. Marcar as regioes no template
Nos arquivos de newsletter, envolva cada area com seus comentarios:

```html
<!-- NOTICIAS:INICIO -->
   ... blocos de noticia 1, 2 e 3 ...
<!-- NOTICIAS:FIM -->
```
```html
<!-- PODCAST:INICIO -->
   ... bloco do episodio do podcast ...
<!-- PODCAST:FIM -->
```
```html
<!-- VIDEO:INICIO -->
   ... bloco do video do YouTube ...
<!-- VIDEO:FIM -->
```

O script so mexe no que estiver ENTRE cada par de marcadores.

### 4. Ajustar o caminho (se necessario)
No topo do `atualiza_conteudo.py`, `GLOB_NEWSLETTER` aponta para
`**/novidades-comunidade/**/*.html`. Ajuste ao nome real da sua pasta.

### 5. Subir os arquivos
Suba `.github/workflows/` e `scripts/` para a raiz do repositorio.

## Como usar
- Automatico: toda segunda 06:00 (Brasilia). Ajuste o `cron` no `.yml`.
- Manual: aba **Actions** -> workflow -> **Run workflow**.

## Cuidados
- Feed do YouTube traz os 15 videos mais recentes; o script usa o primeiro (mais novo).
- Feed do podcast traz os episodios em ordem; o script usa o mais recente.
- Se uma fonte exigir login (ex.: secao privada do forum), o feed publico vem vazio e o
  bloco e mantido - sem quebrar os outros.
- O commit usa [skip ci] para nao disparar workflows em cadeia.
