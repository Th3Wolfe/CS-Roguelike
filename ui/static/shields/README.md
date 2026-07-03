# Escudos dos times

Coloque aqui um arquivo PNG por time, nomeado em minúsculas, espaços/caracteres
especiais trocados por hífen. A HUD carrega automaticamente
`/ui/static/shields/<slug>.png` — se o arquivo não existir, cai de volta pro
emoji padrão sem quebrar o layout.

Tamanho recomendado: quadrado, 128x128 ou 256x256, fundo transparente
(a HUD já recorta em círculo).

## Adversários NPC (systems/team_factory.py -> TEAM_NAMES)

| Time            | Arquivo esperado        |
|-----------------|--------------------------|
| FURIA           | furia.png                |
| Loud            | loud.png                 |
| Imperial        | imperial.png             |
| paiN            | pain.png                 |
| MIBR            | mibr.png                 |
| RED Canids      | red-canids.png           |
| Sharks          | sharks.png               |
| BOOM            | boom.png                 |
| Natus Vincere   | natus-vincere.png        |
| G2              | g2.png                   |
| FaZe            | faze.png                 |
| Astralis        | astralis.png             |
| Vitality        | vitality.png             |
| Team Spirit     | team-spirit.png          |
| Cloud9          | cloud9.png               |
| Heroic          | heroic.png               |
| ENCE            | ence.png                 |
| Complexity      | complexity.png           |
| BIG             | big.png                  |
| Mouz            | mouz.png                 |

## Seu time

O escudo do SEU time também usa esse mesmo mecanismo — o nome vem do que
você digitar no draft. Se você sempre joga com o mesmo nome de time (ex:
"FURIA"), o mesmo arquivo acima já serve. Caso jogue com nomes variados,
os que não tiverem arquivo correspondente simplesmente mostram o emoji 🛡️.
