"""Consolida evidências reais; não executa testes nem altera arquivos fora do lab."""
from __future__ import annotations

import base64
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from run_lab import SCENARIOS

LAB = Path(__file__).resolve().parent
RESULTS = LAB / "results"
TZ = timezone(timedelta(hours=-3))


def read(name: str):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def main() -> None:
    summary = read("summary.json")
    versions = read("versions.json")
    preservation = read("preservation.json")
    metadata = read("lab-metadata.json")
    groups = {}
    for name in SCENARIOS:
        path = RESULTS / (name + ".json")
        if path.exists():
            groups[name] = json.loads(path.read_text(encoding="utf-8"))
    all_rows = [row for rows in groups.values() for row in rows]
    assert len(all_rows) == summary["executed_cases"]
    assert len({r["case"] for r in all_rows}) == len(all_rows)
    first = min(datetime.fromisoformat(r["executed_at"]) for r in all_rows).astimezone(TZ)
    last = max(datetime.fromisoformat(r["executed_at"]) for r in all_rows).astimezone(TZ)
    passed = sum(r["passed"] for r in all_rows)
    table = ["| Cenário | Executados | Aprovados | Reprovados | Interpretação |", "|---|---:|---:|---:|---|"]
    descriptions = {
        "baseline": "Reprodução conhecida aprovada; fixtures não são produção",
        "candidate-root": "Candidata original insuficiente em diretórios com regras próprias",
        "candidate-vhost": "Política aprovada neste modelo de TLS direto",
        "merge-baseline": "Marcador herdado presente",
        "merge-candidate": "Perda do marcador herdado demonstrada, não uma configuração segura",
        "precedence-directory": "Hipótese anterior refutada; resultados originais preservados",
        "precedence-directory-verified": "RewriteRule venceu com ordem textual invertida",
        "precedence-vhost": "Precedência confirmada; três negativos TLS/destino aprovados",
        "proxy-root-naive": "Dois loops esperados detectados: candidata insegura neste cenário",
        "proxy-vhost-naive": "Dois loops esperados detectados: mover só para o vhost não resolve TLS",
        "proxy-edge": "Defeito de /Blog sem barra: três saltos com retorno intermediário a HTTP",
        "proxy-edge-fixed": "Política corrigida aprovada neste proxy controlado",
        "proxy-edge-fixed-query": "Query literal preservada na correção exata de barra",
        "proxy-edge-fixed-headers": "Header forjado sobrescrito; origem em HTTP e corpo preservado",
    }
    for name in SCENARIOS:
        if name not in groups:
            table.append(f"| {name} | Não executado | — | — | Não atribuir aprovação |")
            continue
        rows = groups[name]
        table.append(f"| `{name}` | {len(rows)} | {sum(r['passed'] for r in rows)} | {sum(not r['passed'] for r in rows)} | {descriptions[name]} |")
    home_table = ["| URL lógica original | GET inicial | HEAD inicial | Saltos | URL final | Status final |", "|---|---:|---:|---:|---|---:|"]
    homes = [r for r in groups.get("candidate-vhost", []) if r["test"] in ("rota:/", "rota:/index.html") and r["method"] == "GET"]
    for row in homes:
        head = next(r for r in groups["candidate-vhost"] if r["original_url"] == row["original_url"] and r["method"] == "HEAD")
        home_table.append(f"| `{row['original_url']}` | {row['initial_status']} | {head['initial_status']} | {row['redirect_count']} | `{row['final_url']}` | {row['final_status']} |")
    failures = Counter(r["test"] for r in groups.get("candidate-root", []) if not r["passed"])
    failure_table = ["| Grupo reprovado na raiz | Casos |", "|---|---:|"] + [f"| `{name}` | {count} |" for name, count in failures.items()]
    parent_before = read("merge-baseline-marker.json")["parent_marker"]
    parent_after = read("merge-candidate-marker.json")["parent_marker"]
    text = f'''# CLIMÁTIS — SEO Lote 5A: resultados do laboratório Apache B2

**Data:** 09/11/2026, America/Sao_Paulo.  
**Medições consolidadas:** {first:%d/%m/%Y %H:%M:%S} a {last:%H:%M:%S} -03:00.  
**Entrega:** laboratório local criado e executado, preservando o site original.  
**Decisão para a hospedagem:** **ainda bloqueado para instalar o B1**, até esclarecer mesclagem e topologia da HostGator e obter nova autorização expressa. Produção não está liberada.

## 1. Resultado principal

Foram registrados **{len(all_rows)} casos**, com **{passed} aprovados e {len(all_rows) - passed} reprovados** nas expectativas individuais. As reprovações são evidência: a candidata da raiz falhou em 60 casos; a primeira solução de borda falhou em seis casos de barra; a hipótese anterior de precedência falhou em dois. Esses resultados não foram apagados ou transformados em aprovação.

A variante de **virtual host com TLS direto passou em 322/322 casos**. A variante de **proxy controlado com política na borda e correção restrita de `/Blog` passou em 322/322**, além de oito casos de query nessa correção e dois casos formais de header forjado/corpo. São soluções demonstradas nos modelos do laboratório, não a configuração confirmada da HostGator.

Os quatro casos aprovados de loop nas variantes ingênuas significam **detecção bem-sucedida do defeito**. Não significam aprovação dessas configurações. O exit code zero do runner indica término operacional e limpeza, não aprovação global de todas as candidatas.

## 2. Infraestrutura utilizada e isolamento

| Componente | Versão/estado observado |
|---|---|
| Docker Desktop | {versions['docker_version']['Server']['Platform']['Name']} |
| Docker Engine/CLI | {versions['docker_version']['Server']['Version']} / {versions['docker_version']['Client']['Version']} |
| Compose | {versions['compose_version']} |
| Apache real | {versions['apache'].splitlines()[0]} |
| PHP CLI e módulo Apache da imagem | {versions['php'].splitlines()[0]} |
| OpenSSL | {versions['openssl'].splitlines()[0]} |
| Python host | 3.12.3, biblioteca padrão |
| Python do cliente isolado | {(RESULTS / 'client-version.txt').read_text(encoding='utf-8').splitlines()[0]} |
| Projeto Compose exclusivo | `{metadata['project']}` |
| Sintaxe global do Apache | `{versions['syntax'].strip()}`; requisições reais também exercitaram `.htaccess` |

Módulos carregados incluem rewrite, alias, dir, ssl, headers, proxy, proxy_http e php. [Versões e módulos completos](results/versions.json).

Docker já estava instalado e o Engine estava em execução. A sessão restrita inicialmente não tinha acesso ao named pipe; a consulta com a permissão de execução necessária encontrou o daemon local. Não foi instalado software no Windows, iniciado/configurado WAMP ou alterado contexto/configuração global do Docker. Uma imagem oficial PHP/Apache foi baixada para o laboratório; o cliente Python utilizou uma imagem já existente.

Imagem base fixada: `{versions['base_image']}`. O digest do cliente e o ID da imagem do último complemento estão em [latest-execution.json](results/latest-execution.json). A imagem foi reconstruída apenas para acrescentar configurações/fixtures desta pasta; as versões do Apache/PHP/base não mudaram. Resultados consolidados incluem rodadas incrementais, com timestamps por caso.

A rede é `internal: true`, sem rota externa padrão. **Não há portas publicadas no Windows.** O cliente temporário compartilha o namespace de rede apenas do servidor Apache ou da borda do próprio laboratório e conecta a `127.0.0.1:80/443`. Cada URL/salto lógico é validado e mapeado para loopback; não há resolução DNS pública dos nomes Climátis. ProxyPass aponta somente para `http://backend:80/` na rede privada.

Os servidores montam somente os certificados em leitura. O cliente monta esta pasta em leitura e apenas `results/` em escrita. Nenhum diretório comercial real, banco, configuração privada, credencial ou socket Docker foi montado/copiado. PHP tem envio de e-mail e saída por URL desabilitados; não há integrações reais. [Compose resolvido](results/compose-resolved.json); os arquivos `*-isolation.json` registram mounts, rede e ausência de PortBindings; `*-client-routes.txt` registra a falta de rota padrão.

Certificado autoassinado exclusivo, com SAN para os dois hosts lógicos, localhost e loopback, confiado **apenas pelo SSLContext do cliente**. Nenhum trust store global ou hosts do Windows foi editado. Os controles negativos rejeitaram CA não confiável, SNI errado e destino lógico externo antes de HTTP/DNS. O certificado de laboratório é autoassinado/CA e pode produzir aviso AH01906 no Apache; não é certificado para publicação. Ele expira em sete dias, conforme o procedimento local; a validação TLS nunca foi desligada.

### Primeira tentativa de topologia

A tentativa inicial previa bindings somente em 127.0.0.1, mas esta instalação não os disponibilizou na rede interna: a prontidão falhou com conexão recusada e **zero casos** foram executados. Essa tentativa está arquivada em [attempt-01/summary.json](results/attempt-01/summary.json), sem aprovações. Foi substituída pelo cliente interno, mantendo o bloqueio de rede externa. Nenhum recurso de outro projeto foi removido.

## 3. O que foi reproduzido e o que permanece simulado

| Camada | Evidência da produção nos relatórios anteriores | Laboratório e limite |
|---|---|---|
| Raiz | Redirect 301 do Lote 1 e ErrorDocument 404 | Cópia controlada dessas diretivas; novas regras sempre em 302 |
| Home | Oito variantes 200, canonical/og:url em index | Baseline reproduz isso; candidatas mudam somente metadados da fixture |
| Comercial | Páginas válidas com caminhos protegidos | Cinco HTMLs sintéticos com marcadores próprios; nenhum HTML comercial copiado |
| Blog | `.htaccess` próprio, RewriteBase /Blog/, front controller, cache/compressão | Bloco padrão reconstruído a partir da descrição; não é cópia do arquivo remoto completo |
| WordPress/PHP | Normalização parcial, artigos/feed/REST | Front controller PHP simula as rotas e parte dos redirects; não é instalação WordPress |
| W3 Total Cache | Plugin e regras confirmados por descrição | Um caminho/cache interno sintético demonstra precedência de regra filha; plugin real ausente |
| Redirecionamentos WordPress | 301 observados anteriormente | Fixtures usam 302 temporários e `X-Redirect-By: Fixture-WordPress`, diferença intencional |
| DirectorySlash | `/Blog` tem cadeia preexistente | Diretório real e mod_dir real; seu 301 automático padrão não foi substituído/desabilitado |
| TLS/proxy | Topologia HostGator desconhecida | TLS direto e proxy Apache reais, ambos locais e descartáveis |

Não foram validados banco, plugins reais, login/admin, cron, cookies de autenticação, nonces, todos os filtros WordPress/W3TC, webhooks, entrega de e-mail ou reCAPTCHA. A API, RSS e upload são fixtures sem efeitos externos. Não afirmar “WordPress integralmente validado”. [Proveniência das regras](rules/PROVENIENCIA.md).

## 4. Matriz consolidada e evidências

{chr(10).join(table)}

A matriz completa está em [matrix.csv](results/matrix.csv). Os JSONs por cenário guardam URL original, método, status inicial, Location, saltos, URL/status final, expectativa, observação, aprovado/reprovado, limitações e timestamps. Headers e corpos são apenas de fixtures. Nos negativos de TLS/destino bloqueado não houve resposta HTTP: status e URL finais ficam nulos. Nos loops, “final” representa a última resposta observada antes de interromper a repetição, não um destino terminal alcançado.

### Oito variantes da home, variante de virtual host/TLS direto

{chr(10).join(home_table)}

GET final contém um canonical absoluto e `og:url` na raiz canônica, inclusive quando há query. HEAD não retorna corpo. A URL canônica não redirecionou a resolução interna de DirectoryIndex. A mesma expectativa da home foi aprovada no proxy corrigido.

### Cobertura funcional da matriz

- Cinco fixtures comerciais nos quatro pares HTTP/HTTPS × www/sem www, GET e HEAD, preservando caminho e conteúdo.
- Blog, artigo, categoria, feed RSS, REST por caminho/query, CSS/JS/imagem, cache sintético, rota interna e 404.
- GET/HEAD e POST com corpo, POST multipart bruto e parseado, PUT, PATCH, DELETE, OPTIONS e CORS/preflight em endpoints sintéticos. Nenhum redirect novo ou perda de método/corpo nos casos com corpo testados; hash, tamanho e upload sintético conferidos.
- Queries com nomes repetidos, parâmetro vazio, `+`, `%20`, `%23`, `%2B`, `%26`, `%3F` e dupla codificação. Comparação literal da URL/query, sem parse e reconstrução que esconda diferenças.
- Caminhos com espaço, `#`, `+`, `&`, percentual codificado e `%3F`, incluindo inexistente final 404. Não foi utilizado UnsafeAllow3F nem alterado AllowEncodedSlashes.
- Lote 1: um 301 histórico direto, com query intacta, nos quatro pares e dois métodos. Os novos redirects ensaiados são 302. O 301 nativo de DirectorySlash é comportamento padrão de baseline, não uma nova regra permanente experimental.
- 404 personalizado interno preserva status; `/404.html` direto continua uma página 200. Não há redirecionamento indiscriminado para home.

## 5. Defeitos encontrados, correções e hipóteses refutadas

### 5.1 Candidata somente na raiz: cobertura parcial

Resultado: **262/322**, com 60 falhas de URL/saltos em rotas com regras filhas. A home do Blog pode aparentar sucesso por normalização da própria aplicação simulada; isso não comprova execução da política pai para REST, recursos ou artigos.

{chr(10).join(failure_table)}

Correção arquitetural ensaiada: colocar a política no virtual host e ajustar apenas o padrão per-server de index para `^/index\\.html$`. A raiz mantém Lote 1/ErrorDocument; o Blog não é editado. Resultado: **322/322** no modelo direto. Não foi inserido RewriteOptions Inherit/InheritDownBefore em nenhum cenário.

### 5.2 Incluir regras próprias pode retirar comportamento herdado

Um `<Directory /var/www>` definia um marcador sem alterar o caminho. Antes das novas regras na raiz, o endpoint respondeu `parent_marker={json.dumps(parent_before)}`. Depois de incluir a candidata, respondeu `parent_marker={json.dumps(parent_after)}`. Os dois resultados foram conferidos automaticamente, além de salvos nos arquivos `merge-*-marker.json`.

Isso demonstra um efeito de mesclagem fora do destino de uma regra específica. **Token e rota sintética não isolam a mesclagem da configuração.** O mesmo tipo de risco é relevante para o B1 v2, que também introduz um conjunto próprio na raiz, embora o seu bloco não tenha sido instalado na hospedagem. Não concluir que regras filhas apagam todas as diretivas pai: o achado se refere ao conjunto mod_rewrite desta configuração. [Apache: herança por diretório](https://httpd.apache.org/docs/2.4/rewrite/htaccess.html#rule-inheritance-with-rewriteoptions).

### 5.3 Correção técnica: precedência entre Redirect e RewriteRule

Os relatórios anteriores afirmaram mod_alias antes de mod_rewrite em `.htaccess`. **O laboratório refutou essa afirmação para Apache 2.4.69:** na colisão `/module-order`, RewriteRule emitiu o Location para `/rewrite-order.html`, tanto no `.htaccess` quanto no virtual host.

A primeira expectativa de `/alias-order.html` foi mantida como **0/2, hipótese refutada** em `precedence-directory.json`. Um segundo teste, colocando Redirect antes de RewriteRule no texto, confirmou novamente `/rewrite-order.html`: **2/2**. Isso não é correção de produção nem mudança silenciosa de um resultado para fazê-lo passar.

O código público Apache 2.4.x consultado é consistente com essa observação: `hook_fixup` do rewrite registra prioridade FIRST, e `fixup_redir` do alias registra MIDDLE. [Fonte mod_rewrite](https://raw.githubusercontent.com/apache/httpd/2.4.x/modules/mappers/mod_rewrite.c), [fonte mod_alias](https://raw.githubusercontent.com/apache/httpd/2.4.x/modules/mappers/mod_alias.c). A explicação textual de processamento consultada diverge nesse ponto; o comportamento medido e as fontes de hooks sustentam a conclusão restrita ao laboratório. Não generalizar a configuração efetiva da HostGator a partir disso.

A exclusão explícita da rota do Lote 1 na regra genérica é, portanto, essencial e foi preservada. Não depender de mover a linha Redirect para cima do arquivo. Os documentos originais não foram alterados nesta tarefa; esta correção fica registrada aqui para sua revisão.

### 5.4 Cenário B: TLS na borda, origem HTTP

O proxy Apache terminou TLS e encaminhou por HTTP para uma origem sem portas publicadas. Aplicar a candidata na origem, seja na raiz seja no vhost, fez a home canônica emitir 302 para si mesma porque `%{{HTTPS}}` da origem era off. `/index.html` foi à raiz e encontrou o mesmo loop. **Quatro contraexemplos detectados e registrados.**

Mover a política para a borda que conhece o TLS eliminou esses loops. A origem ficou sem a política HTTPS ingênua. A fixture de aplicação só reconhece o protocolo encaminhado porque a rede é controlada e o proxy remove/sobrescreve o header recebido. Dois controles formais com X-Forwarded-Proto forjado mostraram origem HTTP e header efetivo igual ao esquema real da borda, com corpo preservado. Isso não autoriza confiar nesse header livremente na HostGator.

### 5.5 Barra em `/Blog`: downgrade e três saltos no primeiro proxy

A primeira política de borda teve seis reprovações: `http://climatis.com.br/Blog` passou por HTTPS www sem barra; o DirectorySlash da origem HTTP devolveu `http://www.climatis.com.br/Blog/`; a borda precisou normalizar outra vez. Foram **três saltos**, com downgrade intermediário. O canônico sem barra também apresentou retorno indevido a HTTP.

Correção **somente no proxy do laboratório**: regra exata GET/HEAD para `/Blog`, antes da normalização genérica, aponta diretamente para `https://www.climatis.com.br/Blog/`, preservando query. Não desabilita DirectorySlash nem modifica WordPress. Resultado: **322/322**, mais **8/8** para query repetida/codificada nessa rota. A regra é uma demonstração para arquitetura controlada, não uma autorização de corrigir essa cadeia isoladamente em configuração superior desconhecida.

## 6. Condições Apache: conclusões verificadas

| Condição/elemento | Resultado e limite |
|---|---|
| `%{{HTTPS}}` | Adequado na camada que termina TLS; na origem HTTP atrás do proxy gerou loop |
| `%{{HTTP_HOST}}` | Hosts conhecidos normalizados; host desconhecido não vira destino arbitrário; proxy preserva Host |
| `%{{THE_REQUEST}}` | Distingue index explícito de DirectoryIndex e fornece caminho bruto codificado; query/path chegaram literais |
| `%{{REQUEST_URI}}` | Exclusão do Lote 1 funcionou; não foi usado como caminho bruto com NE na substituição genérica |
| `%{{REQUEST_METHOD}}` | Novas regras só GET/HEAD; métodos com corpo/preflight dos endpoints testados não receberam redirecionamento |
| `%{{IS_SUBREQ}}` | Home canônica/DirectoryIndex e recursos funcionaram sem redirect indevido; não foi publicado dump de subrequisições |
| `%{{ENV:REDIRECT_STATUS}}` | Rota interna chegou ao echo com valor 200 e manteve processamento sem novo redirect externo |
| RewriteEngine/mesclagem | Sintaxe aceita, mas regras próprias retiraram o marcador herdado; exige análise antes de B1 |
| Redirect/RewriteRule | RewriteRule venceu a colisão local nas duas ordens textuais; Lote 1 preservado por exclusão explícita |

AllowOverride All e FollowSymLinks foram definidos somente para o DocumentRoot sintético do container. Isso não comprova permissões/overrides da HostGator. Nenhum filtro de URL foi relaxado para aceitar casos artificiais. O laboratório não mede todos os aliases, opções ou patches de uma hospedagem comercial.

## 7. Regras candidatas recomendadas após os ensaios

| Topologia efetivamente confirmada no futuro | Artefato demonstrado | Pré-condição |
|---|---|---|
| TLS direto na camada Apache que controla todos os caminhos | [candidate-vhost-302.conf](rules/candidate-vhost-302.conf) | Inserir no contexto correto dos vhosts, reconciliado com configuração real e Lote 1 |
| TLS em proxy/borda sob controle do administrador | [candidate-edge-fixed-302.conf](rules/candidate-edge-fixed-302.conf) | Política única na borda; origem sem teste HTTPS incompatível; protocolo encaminhado autenticado/sanitizado para a aplicação |
| Somente `.htaccess` da raiz, herança/proxy desconhecidos | [candidate-root.htaccess](rules/candidate-root.htaccess) | **Não recomendada para publicação** com a evidência atual; 60 falhas no modelo e risco de mesclagem |

Os arquivos de `apache/` possuem caminhos e certificados exclusivos de Docker; não são arquivos para copiar no cPanel. Os candidatos usam 302 e permanecem exemplos experimentais. Transformação futura para 301 exigirá pacote reconciliado, testes de hospedagem aprovados e autorização de publicação. Não alterar o Redirect 301 do Lote 1.

Correção específica de barra demonstrada na borda (complementa, não substitui, o bloco de política):

```apache
RewriteEngine On
RewriteCond %{{HTTP_HOST}} ^(?:www\\.)?climatis\\.com\\.br(?::[0-9]+)?$ [NC]
RewriteCond %{{REQUEST_METHOD}} ^(?:GET|HEAD)$
RewriteCond %{{IS_SUBREQ}} =false
RewriteCond %{{ENV:REDIRECT_STATUS}} ^$
RewriteCond %{{THE_REQUEST}} \\s/Blog(?:\\?|\\s)
RewriteRule ^/Blog$ https://www.climatis.com.br/Blog/ [R=302,L,NE]
```

Não usar esse padrão com barra inicial em `.htaccess`; ele foi ensaiado em contexto virtual host da borda. Outras pastas/aliases podem exigir tratamento próprio; não generalizar a correção de `/Blog` para qualquer diretório.

## 8. Riscos remanescentes e próximo passo na hospedagem

Faltam versão/patches Apache, DocumentRoot por host/porta, regras superiores, overrides/symlinks, herança efetiva, proxies/CDN/WAF, terminação TLS, sanitização de headers, configuração completa do Blog/W3TC e inventário de consumidores reais. Não há evidência local que os substitua.

**Próximo passo recomendado: diagnóstico privado somente leitura com o administrador**, antes de instalar B1. Pedir resumo/exportação sanitizada desses pontos, sem credenciais. Em particular, verificar se introduzir um ruleset na raiz retiraria alguma política herdada. Se isso não puder ser assegurado, não instalar o B1 v2 ali; preparar um ensaio isolado em camada apropriada com o responsável.

Se esses pré-requisitos forem satisfeitos e houver nova autorização expressa, o B1 supervisionado deverá:

1. Usar backup binário do `.htaccess` efetivo vigente, hashes, permissões e restauração imediata; não usar a cópia local do site como backup.
2. Reconciliar o procedimento B1 v2 com a mesclagem real, sem adicionar Inherit para obter um positivo artificial. A correção de precedência deste relatório deve integrar essa revisão.
3. Gerar seletor privado novo e rotas sintéticas exclusivas, com apenas 302, sem publicar valores ou informações internas. O identificador/token do laboratório não deve ser transferido para produção.
4. Medir controles normais antes/durante/depois e GET/HEAD nos quatro pares raiz/Blog, registrando primeiro status/Location sem seguir automaticamente.
5. Tratar ausência de marcador como inconclusiva; HTTPS externo recebendo ramo de HTTP exige esclarecer a topologia, não confiar em X-Forwarded-Proto do visitante.
6. Interromper no primeiro 5xx/403 novo, alteração normal, marcador sem seletor, inconsistência ou fim da janela; retirar o bloco mesmo com sucesso e comprovar rollback.

Esse procedimento é uma proposta posterior. **O B1 não foi executado nem autorizado nesta tarefa.** Sucesso local não libera produção ou prova que a HostGator use a arquitetura A ou B. Também não houve nova consulta ao GSC ou rastreamento do site publicado.

## 9. Reprodução, encerramento e preservação

As instruções completas estão no [README](README.md). Nesta entrega o laboratório já está preparado; `lab.ps1 -Build` executa a matriz, e `-Only` permite repetir um cenário sem apagar as evidências dos outros. Somente dependências de biblioteca padrão Python são utilizadas.

O runner encerrou/removou containers e rede do projeto exclusivo: **{summary['cleanup']['successful']}**. A imagem/cache Docker e os artefatos do laboratório foram mantidos para reprodução. Não houve prune global nem alteração de outros projetos.

Hash de **{preservation['original_count']} arquivos originais** conferido; originais alterados: **{len(preservation['changed_originals'])}**. Os três documentos obrigatórios foram consultados e preservados, com hashes registrados em [lab-metadata.json](results/lab-metadata.json). [Conferência de preservação e Git](results/preservation.json). O Git permanece na branch main/HEAD original; aparecem apenas arquivos novos desta pasta, sem commit, push ou operação Git remota.

Nenhum arquivo existente fora do laboratório foi escrito. Este relatório foi criado **dentro de `seo-lab/lote-5a-apache/`**, respeitando o limite da tarefa. Não houve alteração no `.htaccess` da HostGator, WordPress publicado, páginas/formulários/integrações comerciais ou Lotes 1–4. Não houve deploy, publicação, edição de hosts/DNS/cPanel, instalação global de programas ou requisição ao site real durante B2.

**Conclusão:** B2 local concluída e documentada. **Ainda bloqueado para avançar à instalação do B1 na HostGator** até os pré-requisitos de mesclagem/topologia serem confirmados e o proprietário conceder nova autorização expressa. As variantes aprovadas são referências para revisão, não um pacote pronto para produção.
'''
    target = LAB / "SEO_LOTE_5A_LAB_APACHE_RESULTADOS.md"
    target.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(target), "executed": len(all_rows), "passed": passed, "failed": len(all_rows) - passed, "originals_changed": len(preservation["changed_originals"])}))


if __name__ == "__main__":
    main()
