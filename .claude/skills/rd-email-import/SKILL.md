---
name: rd-email-import
description: Checklist final e script de validação para preparar um template de e-mail HTML (deste repositório) para importação no RD Station Marketing. Use sempre que o usuário disser que vai importar/subir um e-mail no RD Station, pedir para "ajustar para o RD", "deixar pronto para importar", "verificar antes de subir", reportar que um e-mail importado "ficou achatado", "estreito", "pequeno no celular", "com bordas estranhas", "sem alinhamento", "colado na borda" ou "com texto minúsculo", ou pedir uma "verificação final" num template de e-mail antes do disparo. Cobre tanto a importação de página completa por URL quanto colar um fragmento em um bloco de HTML dentro de um template do RD.
---

# Preparar e-mail para o RD Station

Este repositório já descobriu, na marra, que o RD Station Marketing trata
o HTML de um jeito que nenhuma documentação oficial descreve direito.
Esta skill existe para não repetir essa descoberta a cada template novo.

## Antes de tudo: duas formas de importar, dois checklists diferentes

O RD Station aceita um template de e-mail de duas formas bem diferentes,
e as regras que funcionam numa **não funcionam** na outra. Pergunte ao
usuário (ou confira pelo que ele já disse) qual caminho ele vai usar:

1. **Página completa**, importada por "Importe seu modelo de Email a
   partir da web" (URL) — o arquivo é um HTML completo, com
   `<html>/<head>/<body>`, like os templates já existentes em
   `dia-do-acbr-2026/*.html`, `novidades-comunidade/*.html` etc.
2. **Bloco**, colado dentro de um bloco de "HTML customizado"/"Código"
   do editor visual de um template do RD já existente — um fragmento
   sem `<html>/<head>/<body>`, como
   `dia-do-acbr-2026/email-app-participantes-bloco-rd.html`.

Se não souber qual o usuário vai usar, pergunte — a maior parte do
checklist abaixo muda de sentido dependendo da resposta. **O bloco é a
opção melhor sempre que ela existir**: o template do RD já fornece
viewport e estrutura responsiva corretos, então o celular renderiza
texto no tamanho normal sem precisar de nenhum truque nosso. A página
completa só devia ser usada quando o RD não oferece a opção de bloco
dentro do template que o usuário quer usar — e, mesmo assim, aceite que
o resultado no celular vai ser um compromisso (veja a seção própria
abaixo).

## Por que essas regras existem (o que já tentamos e não funcionou)

Vale entender a causa antes de aplicar a regra de cabeça — ajuda a
adaptar quando um template fugir do padrão:

- **RD não confia em `<style>`/`<head>`.** O próprio modal de "Regras de
  importação" do RD avisa: evite CSS em `<style>` no cabeçalho, prefira
  tudo inline (eles recomendam até o Premailer pra isso). Na prática,
  isso significa que `@media` para responsividade **não sobrevive** —
  nem na importação por URL nem no bloco. Não adianta tentar resolver o
  celular com media queries aqui.
- **A importação por URL mede a página numa viewport estranha.** Testamos
  largura fixa (600px), fluida (`width:100%`), `auto` e a técnica
  "fluid-hybrid" (atributo HTML `width="100%"` + `style` só com
  `max-width`) numa página completa — nenhuma combinação resolveu
  desktop E celular ao mesmo tempo nesse caminho. É por isso que o bloco
  é preferível sempre que disponível: ele tira a página completa (e essa
  medição estranha) da equação, deixando o próprio template do RD
  controlar a largura.
- **Sites como diadoacbr.com.br entregam WebP em URLs `.png`.** O Gmail
  perde a transparência nessas imagens (fica preto/serrilhado). Por
  isso hospedamos imagem real (PNG de verdade) no próprio repositório
  quando a fonte externa é suspeita — veja `scripts/valida_email.py`.

## Checklist — página completa (importação por URL)

- Largura do card **fixa em px** (`width="600"` + `style="width:600px"`),
  nunca `%`/`auto`: é a única coisa que mede certo na importação por
  URL, nos testes que já fizemos.
- `<meta name="color-scheme" content="light">` +
  `<meta name="supported-color-schemes" content="light">` +
  `<meta name="x-apple-disable-message-reformatting">` no `<head>`,
  para não inverter logos brancos no modo escuro.
- Se, depois de travar a largura em px, o texto vier minúsculo no
  celular (porque não há bloco disponível e o `<meta viewport
  content="width=device-width,initial-scale=1">` padrão deixa o celular
  encolher tudo pra caber na tela): considerar trocar para
  `<meta name="viewport" content="600">` — texto fica legível, ao custo
  de a pessoa precisar arrastar horizontalmente para ver a largura
  toda. **Isso é um trade-off, não uma solução — explique ao usuário
  antes de aplicar**, e prefira migrar para bloco se possível em vez de
  aceitar esse custo.

## Checklist — bloco (fragmento para colar num template existente)

- **Sem** `<html>`, `<head>`, `<body>`, `<style>` nem
  `<meta name="viewport">` — o template do RD já fornece tudo isso;
  incluir de novo só adiciona ruído (na melhor das hipóteses) ou
  quebra a importação (na pior).
- Card envolvido em `<center>…</center>` **e** com `align="center"` na
  tabela — sem o wrapper de página, ele tende a colar na esquerda em
  vez de ficar centralizado dentro do bloco/coluna do RD.
- Largura do card: `width="100%"` + `style="max-width:600px"` (sem
  `width:` fixo no style) — deixa o card preencher a largura que o
  bloco/coluna do RD fornecer, até 600px.
- **Sem borda nem `border-radius`** na tabela externa do card — ele deve
  se fundir ao fundo do template do RD, não aparecer como um cartão à
  parte. (Elementos internos — botões, caixinhas de destaque, badges
  numerados — continuam podendo ter a própria borda/raio; a regra é só
  para o contêiner mais externo.)
- Padding lateral das linhas de conteúdo **reduzido ao mínimo, ~12px**
  — bem menor que os 32px usados nas páginas completas — para o texto
  aproveitar quase toda a largura disponível. Botões e caixas internas
  podem manter padding maior (16-24px), já que fazem parte do desenho
  deles, não da margem do card.
- Imagens largas o bastante para ficarem desalinhadas quando o
  conteúdo ganha mais largura (ex.: um banner pensado para um padding
  de 32px, agora com só 12px) precisam de `align="center"` no `<td>` e
  `margin:0 auto` no próprio `<img>` para não ficarem coladas à
  esquerda.
- Logo/imagens de cabeçalho não devem ser maiores que o necessário —
  já vimos um logo de 200px ficar "grande demais" no celular depois
  que o resto do bloco passou a usar a largura real do dispositivo;
  ~160px costuma ser um tamanho mais seguro para um logo de topo.
- Se o próprio importador/editor do RD adiciona um padding próprio ao
  redor do bloco (pergunte ao usuário, ou confira num teste real),
  ajuste o `max-width` do card para compensar: `600 - 2 × padding_do_RD`.
- O texto de pré-visualização (preheader) não cabe num fragmento — ele
  depende de vir logo após `<body>`. Avise o usuário para configurar
  isso no campo próprio do RD, não tente embutir no bloco.

## Rode o validador antes de publicar

`scripts/valida_email.py` já checa boa parte disso automaticamente —
ele **detecta sozinho** se o arquivo é bloco ou página completa (pela
ausência/presença de `<html>`) e aplica o checklist certo:

```
python3 scripts/valida_email.py caminho/do/email.html
```

Resolva todo `ERRO`. Avalie cada `AVISO` com juízo — alguns domínios
(como `doity.com.br` neste ambiente) são bloqueados pelo proxy desta
sessão e aparecem como link/imagem inacessível mesmo sendo URLs de
produção válidas; não é um defeito do template.

Links úteis do próprio validador:
- `--fix` converte imagens WebP disfarçadas de PNG/JPG para PNG real,
  hospeda no repositório (`<pasta>/img/<nome do e-mail>/`) e já
  reescreve o `src` para `raw.githubusercontent.com`.

## Fluxo de trabalho

1. Pergunte/confirme o modo (bloco vs. página completa) se não estiver
   claro.
2. Aplique o checklist correspondente diretamente no HTML.
3. Rode `python3 scripts/valida_email.py <arquivo>` e resolva os erros.
4. Publique seguindo o fluxo de git já estabelecido neste repositório
   (branch a partir do `main` atual, commit, push, PR, merge).
5. Avise o usuário do que foi ajustado e por quê — alguns itens (como
   o trade-off do viewport em página completa) têm consequência direta
   na experiência de quem recebe o e-mail, e o usuário deve saber disso
   antes de disparar.
