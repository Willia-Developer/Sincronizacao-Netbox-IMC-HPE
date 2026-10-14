# Passo a passo: plugins instalados e atualização do NetBox

Revisado em 14/10/2026. Ambiente: `<DIRETORIO_NETBOX>`, Docker Compose.
Versão confirmada no contêiner: **4.7.2-Docker-5.1.1**. Imagem em uso:
`netbox-local:4.7.2-all-plugins`. Aplicação, worker, PostgreSQL e os dois
serviços Valkey estavam saudáveis na revisão. Este documento descreve uma
execução futura; a revisão não instalou plugins nem atualizou a aplicação.

## 1. Plugins já instalados

| Plugin | Pacote Python | Versão | Nome em PLUGINS |
|---|---|---|---|
| Topology Views | netbox-topology-views | 4.7.0 | netbox_topology_views |
| Floorplan | netbox-floorplan-plugin | 0.10.0 | netbox_floorplan |
| NextBox UI | nextbox-ui-plugin | 1.0.7 | nextbox_ui_plugin |
| DNS | netbox-plugin-dns | 1.7.3 | netbox_dns |
| BGP | netbox-bgp | 0.20.2 | netbox_bgp |
| Attachments | netbox-attachments | 12.0.0 | netbox_attachments |
| Documents | netbox-documents | 0.8.5 | netbox_documents |
| Map | netbox-map | 0.12.0 | netbox_map |

Esses oito pacotes e sua ativação foram conferidos no contêiner em execução.
Secrets não faz parte da instalação e não deve ser acrescentado neste roteiro.

## 2. Arquivos necessários

- `plugin_requirements.txt`: versões exatas dos oito pacotes.
- `configuration/plugins.py`: ativação e opções dos plugins.
- `Dockerfile-Plugins`: imagem base, instalação, patches e arquivos estáticos.
- `plugin-install/constraints.txt`: restrições das dependências do conjunto atual.
- `plugin-install/patch-nextbox.py`: adaptações de NextBox UI e Documents.
- `docker-compose.yml` e `docker-compose.override.yml`: serviços, imagem e volumes.
- `configuration/` e `env/`: configuração e segredos de execução.

O override é necessário: ele seleciona a imagem personalizada para **netbox e
netbox-worker**. O Compose principal sozinho seleciona a imagem comunitária sem
os plugins. Execute os comandos na pasta indicada, preservando o override.

Não execute `plugin-install/deploy.sh` novamente: é um script da implantação
inicial dos seis plugins adicionais, com pressupostos sobre a imagem anterior.
`plugin-install/test-compose.yml` usa infraestrutura compartilhada com a
instalação local; não o trate como homologação isolada.

## 3. Conferência antes de qualquer mudança

Execute em Bash, na mesma sessão para preservar as variáveis do roteiro:

```bash
cd <DIRETORIO_NETBOX>
set -euo pipefail
umask 077
docker compose config --quiet
docker compose ps
cat plugin_requirements.txt
cat configuration/plugins.py
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py check
```

Preserve `SECRET_KEY`, `API_TOKEN_PEPPERS`, credenciais do banco e configurações
de autenticação. Não publique arquivos `env`, backups ou a saída completa de
`docker compose config`, pois podem conter segredos.

## 4. Instalar ou reconstruir os oito plugins nas versões atuais

Este fluxo serve para o projeto existente ou uma cópia completa dele com os
arquivos da seção 2. Não é um instalador de Docker/PostgreSQL do zero.

### 4.1 Conferir os pacotes e a ativação

O conteúdo de `plugin_requirements.txt` deve ser:

```text
netbox-topology-views==4.7.0
netbox-floorplan-plugin==0.10.0
nextbox-ui-plugin==1.0.7
netbox-plugin-dns==1.7.3
netbox-bgp==0.20.2
netbox-attachments==12.0.0
netbox-documents==0.8.5
netbox-map==0.12.0
```

`configuration/plugins.py` deve habilitar os oito nomes da tabela. Preserve
`PLUGINS_CONFIG`: ele habilita o salvamento de coordenadas do Topology Views e
configura a aba de Attachments nos aplicativos já selecionados.

### 4.2 Construir antes de interromper o serviço

Para uma reconstrução, use uma tag nova, sem sobrescrever a imagem em execução:

```bash
CANDIDATE_IMAGE="netbox-local:4.7.2-all-plugins-rebuild-$(date +%Y%m%d-%H%M%S)"
docker build -f Dockerfile-Plugins -t "$CANDIDATE_IMAGE" .
```

A instalação dos pacotes ocorre no build, dentro do ambiente virtual da imagem.
O Dockerfile aplica os patches e executa `collectstatic`. Não é necessário
instalar por `pip` manualmente em um contêiner em execução.

Adaptações locais obrigatórias neste conjunto:

- NextBox UI 1.0.7: interpreta a versão sem o sufixo Docker, inclusive nas migrações.
- Documents 0.8.5: adapta as ações antigas para `BulkExport` e `BulkDelete`.

O script possui verificações que interrompem o build se o código esperado mudar.
Se ocorrer essa falha, revisar a compatibilidade; não remover as verificações
para forçar a construção. As restrições atuais também podem impedir uma versão
nova de plugin: precisam ser revisadas junto com o destino.

Homologue a imagem em uma instalação separada, com banco, volumes, rede e
credenciais próprios, a partir de uma restauração do backup. Bloqueie e-mails,
webhooks e sincronizações para produção. Teste migrações, páginas, permissões,
criação e leitura de anexos/documentos, além das integrações usadas.

### 4.3 Backup final antes de ativar a imagem

Suspenda sincronizadores e outros escritores externos, aguarde jobs em execução
e pare aplicação e worker. Não deixe outras réplicas escrevendo.

```bash
BACKUP_DIR="$PWD/backups/manutencao-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -a configuration env plugin-install Dockerfile-Plugins \
  plugin_requirements.txt docker-compose.yml docker-compose.override.yml "$BACKUP_DIR/"
if [ -f .env ]; then cp -a .env "$BACKUP_DIR/"; fi
NETBOX_CID="$(docker compose ps -a -q netbox)"
test -n "$NETBOX_CID"
PREVIOUS_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$NETBOX_CID")"
PREVIOUS_IMAGE="netbox-local:backup-$(basename "$BACKUP_DIR")"
docker image tag "$PREVIOUS_IMAGE_ID" "$PREVIOUS_IMAGE"
printf '%s\n' "$PREVIOUS_IMAGE" > "$BACKUP_DIR/previous-image.txt"
# Mantém uma cópia recuperável mesmo se as imagens locais forem removidas.
docker image save "$PREVIOUS_IMAGE" > "$BACKUP_DIR/previous-image.tar"
docker compose stop netbox-worker netbox
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP_DIR/database.dump"
test -s "$BACKUP_DIR/database.dump"
docker compose exec -T postgres pg_restore --list \
  < "$BACKUP_DIR/database.dump" > "$BACKUP_DIR/database-contents.txt"
for directory in media reports scripts; do
  docker cp "$NETBOX_CID:/opt/netbox/netbox/$directory" "$BACKUP_DIR/$directory"
done
tar -czf "$BACKUP_DIR/persistent-files.tar.gz" -C "$BACKUP_DIR" media reports scripts
(cd "$BACKUP_DIR" && sha256sum database.dump persistent-files.tar.gz previous-image.tar > SHA256SUMS)
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS)
printf 'Backup: %s\n' "$BACKUP_DIR"
```

Se o backup falhar, não prossiga com a migração. A listagem do dump verifica seu
formato, mas não substitui um teste de restauração. Mantenha cópia do backup fora
do host, com acesso restrito. A pasta contém banco e segredos.

### 4.4 Selecionar a imagem, migrar e iniciar

Depois do backup, edite `docker-compose.override.yml`: substitua o campo `image`
de **netbox e netbox-worker** pela tag exata exibida por:

```bash
printf '%s\n' "$CANDIDATE_IMAGE"
```

Preserve portas, volumes e demais configurações. Depois:

```bash
docker compose config --quiet
docker compose run --rm --no-deps --entrypoint /bin/bash netbox -c \
  'set -e; mkdir -p /opt/netbox/netbox/media/netbox-attachments; /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate --no-input; /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py check'
docker compose up -d --no-build --wait --wait-timeout 600 netbox netbox-worker
```

Em falha de migração, não inicie a versão antiga contra esse banco: use a
restauração da seção 7. Não execute `docker compose down -v`.

## 5. Validar depois da instalação ou atualização

```bash
docker compose ps
docker compose logs --tail=100 netbox netbox-worker
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py check
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py migrate --check
curl -fsS -o /dev/null -w 'Login HTTP %{http_code}\n' http://127.0.0.1:8080/login/
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py shell -c \
  'from django.conf import settings; from importlib.metadata import version; print(settings.VERSION); print(settings.PLUGINS); packages=["netbox-topology-views","netbox-floorplan-plugin","nextbox-ui-plugin","netbox-plugin-dns","netbox-bgp","netbox-attachments","netbox-documents","netbox-map"]; print([(p, version(p)) for p in packages])'
```

Compare as versões com o destino planejado. Acesse com login os oito plugins,
confira dispositivos, sites, racks e dados dos plugins; teste as permissões de
um usuário comum, os tokens existentes, integrações e o worker. Anexos e
Documents precisam também de upload/download de teste em objeto próprio de
validação. HTTP 200 na tela de login não comprova todos esses fluxos.

Retome sincronizadores e acessos depois da validação. Registre imagem, versões,
backup e resultado dos testes em `PLUGINS-INSTALADOS.md` e no histórico de atualização.

## 6. Atualizar o NetBox mantendo esses oito plugins

1. Escolha uma versão exata de destino. Consulte as notas de todas as versões
   intermediárias e a compatibilidade dos oito plugins com NetBox/Python/Django.
   Siga eventuais versões intermediárias obrigatórias nas notas oficiais.
2. Prepare uma cópia separada dos arquivos de build. Atualize `FROM` no
   `Dockerfile-Plugins` para a tag Docker completa de destino. Alterar apenas
   `VERSION` não atualiza a imagem personalizada selecionada pelo override.
3. Ajuste `plugin_requirements.txt` para as versões compatíveis. Gere/revise
   `plugin-install/constraints.txt` para a imagem de destino: o arquivo atual
   fixa dependências e plugins do conjunto 4.7.2 e não deve ser reaproveitado
   cegamente em outra versão do NetBox.
4. Revise `plugin-install/patch-nextbox.py`. Confirme se os patches ainda são
   necessários e adapte-os ao código de destino. Não presuma compatibilidade
   dos oito plugins com uma versão futura.
5. Confira usuário, entrypoint, healthcheck e configuração exigidos pela nova
   imagem. O ambiente atual usa `netbox:root`, `/opt/netbox/health.sh` e worker;
   não possui serviço separado de housekeeping.
6. Construa com tag nova pelo comando da seção 4.2, usando o Dockerfile preparado
   e uma tag correspondente ao destino. Não use `latest`.
7. Homologue atualização e restauração em ambiente isolado antes da manutenção.
   Preserve PostgreSQL/Valkey nas versões atuais durante a mudança, salvo se
   houver uma migração de infraestrutura previamente preparada.
8. Faça o backup final da seção 4.3 **antes de editar os arquivos ativos**.
   Transfira os arquivos homologados, configure a tag de destino em ambos os
   serviços e aplique a seção 4.4. Execute a validação da seção 5.

Para requisitos corporativos, ensaio e recuperação, consulte também o
[procedimento corporativo](PROCEDIMENTO_CORPORATIVO_ATUALIZACAO_NETBOX.md).
`ATUALIZACAO-4.7.2.md` registra a atualização já realizada de 4.2.9 para 4.7.2;
seus dois plugins descrevem aquele momento, anterior aos seis plugins adicionais.

## 7. Recuperar em caso de falha

A restauração perde alterações posteriores ao backup. Recupere um conjunto
coerente: imagem, configuração, banco, arquivos persistentes e segredos anteriores.

1. Bloqueie escritores e pare aplicação/worker. Preserve logs da falha.
2. Defina `BACKUP_DIR` para o backup correto e confira `sha256sum -c SHA256SUMS`
   dentro dele. Recupere a imagem com `docker image load -i
   "$BACKUP_DIR/previous-image.tar"` se necessário.
3. Restaure os arquivos Compose, Dockerfile, requisitos, `plugin-install/`,
   `configuration/`, `env/` e `.env` do backup. Reconcilie arquivos novos para
   não deixar configurações residuais. Use em ambos os serviços a imagem salva
   em `previous-image.txt` e evite reconstruí-la durante a recuperação.
4. Prepare uma base PostgreSQL **vazia** de recuperação, mantendo aplicação e
   worker parados. Restaure o dump e aponte `DB_NAME` da aplicação para essa
   base. O banco parcialmente migrado deve ser preservado para investigação.
5. Recupere `media`, `reports` e `scripts` em volumes vazios de recuperação,
   configure os mounts correspondentes e confira proprietário/permissões.
   Copiar por cima dos volumes alterados pode deixar arquivos residuais.
6. Confira as filas antes de iniciar o worker: jobs criados pelo código novo
   podem ser incompatíveis. Não limpe Redis/Valkey indiscriminadamente.
7. Inicie com `--no-build`, valide pela seção 5 e retome os escritores.

A seção 10 do [procedimento corporativo](PROCEDIMENTO_CORPORATIVO_ATUALIZACAO_NETBOX.md#10-rollback-por-restauracao)
traz o comando `pg_restore` e os requisitos da base vazia. Não basta trocar a
imagem após migrações, nem executar NetBox 4.2.9 contra o banco de 4.7.2.

## 8. Fontes e documentação histórica

Fluxo conferido com a documentação oficial em 14/10/2026:

- [Instalação de plugins](https://netbox.readthedocs.io/en/stable/plugins/installation/).
- [Plugins em netbox-docker](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).
- [Atualização do NetBox](https://netbox.readthedocs.io/en/stable/installation/upgrading/).

As páginas `stable` podem mudar: use as notas e instruções da versão escolhida
antes de executar uma atualização. `PASSO_A_PASSO_COMPLETO.md` é histórico de
4.2.9, não o roteiro para reconstruir o ambiente atual.
