# Procedimento corporativo de atualização do NetBox

| Controle documental | Informação |
|---|---|
| Identificador | POP-NETBOX-001 |
| Versão do documento | 1.0 |
| Data | 11/10/2026 |
| Classificação sugerida | Uso interno |
| Proprietário proposto | Equipe de Infraestrutura / Plataforma |
| Revisor técnico | A designar |
| Aprovador | A designar pelo responsável pelo serviço |
| Status | Proposta para revisão e aprovação interna |
| Implementação de referência | Docker Compose, NetBox 4.7.2 com plugins |

Este documento estabelece um procedimento operacional para uso corporativo. Sua adoção como norma oficial depende da aprovação interna da organização. As fontes oficiais do NetBox e do NetBox Docker estão relacionadas ao final; este documento não foi emitido nem homologado pelos mantenedores desses projetos.

## 1. Objetivo e abrangência

Atualizar o NetBox com rastreabilidade, proteção dos dados, indisponibilidade planejada e capacidade de recuperação comprovada. O procedimento principal cobre Docker Compose com imagem personalizada para plugins, PostgreSQL e Redis/Valkey. Aplica-se a desenvolvimento, homologação e produção, com os controles de mudança definidos pela organização.

Instalações por Git/arquivo de distribuição, Kubernetes, serviços gerenciados de banco ou alta disponibilidade exigem adaptação previamente homologada. A seção 12 orienta essas variações. Os comandos deste documento são instruções para uma execução futura; criar esta documentação não executa uma nova atualização.

## 2. Responsabilidades

| Papel | Responsabilidade e evidência |
|---|---|
| Responsável pelo serviço | Definir criticidade, RTO/RPO e aceitar o resultado funcional |
| Executor de plataforma | Preparar artefatos, executar atualização e registrar logs |
| DBA ou responsável pelo PostgreSQL | Validar permissões, backup, restauração e integridade |
| Responsável por integrações | Suspender escritores, testar APIs e retomar sincronizações |
| Segurança | Revisar acesso, segredos e mudanças relevantes à autenticação |
| Gestor de mudanças/CAB, conforme política interna | Autorizar janela, risco e plano de recuperação |
| Validador funcional | Testar fluxos representativos e registrar aceite |

Em equipes menores, uma pessoa pode acumular funções. A aprovação deve seguir a segregação de funções definida pela empresa.

## 3. Registro da mudança

Preencher antes da execução:

| Campo | Valor a preencher |
|---|---|
| Identificador da mudança | CHG-… |
| Ambiente, hosts e projeto Compose | … |
| Versão atual / versão de destino | … / … |
| Justificativa e benefícios | Correção, segurança, suporte ou necessidade funcional |
| Plugins e respectivas versões | … |
| Imagens e digests aprovados | … |
| Integrações dependentes e seus responsáveis | … |
| Janela e indisponibilidade comunicada | Início e término, com fuso horário |
| RTO / RPO aprovados | … |
| Tempo de atualização medido em homologação | … |
| Tempo de restauração medido em homologação | … |
| Horário limite para decidir rollback | Término da janela menos restauração e validação |
| Backup e comprovação de restauração | Local, identificador e evidência |
| Executor, validador e aprovador | … |
| Canal de acompanhamento e escalonamento | … |

RTO é o prazo de recuperação aceitável. RPO é a perda de dados aceitável. No fluxo com suspensão de todas as escritas e backup final consistente, a meta é recuperar o estado do início da manutenção. Escritas aceitas após esse backup não estarão automaticamente disponíveis no rollback.

## 4. Condições para iniciar e interromper

### 4.1 Condições de início

- Mudança aprovada e janela comunicada aos usuários e responsáveis pelas integrações.
- Notas de todas as versões intermediárias revisadas; compatibilidade de plugins, scripts e clientes de API comprovada.
- Atualização e restauração ensaiadas em homologação com dados representativos.
- Artefato de destino construído e aprovado; imagem anterior disponível para recuperação.
- Capacidade de disco suficiente para backup, imagens, restauração e crescimento temporário do banco, com margem medida no ensaio.
- Responsáveis e acessos necessários disponíveis durante a janela.
- Plano para impedir escritas de usuários, automações, workers e sistemas externos.

### 4.2 Critérios de interrupção ou rollback

Interromper antes de migrar se houver plugin incompatível, falha no backup, teste de restauração inconclusivo, segredo obrigatório ausente ou divergência entre artefato homologado e artefato de produção.

Durante a execução, decidir rollback se houver migração com erro, perda de integridade, falha de autenticação crítica, integração essencial incompatível ou impossibilidade de cumprir a janela. Atingir o horário limite registrado na mudança exige uma decisão explícita do responsável; não prolongar a manutenção sem avaliação.

## 5. Preparação técnica e homologação

### 5.1 Inventário

No diretório da implantação, usando o mesmo contexto Docker, projeto Compose, arquivos `-f` e variáveis usados em produção:

```bash
cd /caminho/da/implantacao/netbox
set -euo pipefail
umask 077

docker context show
docker compose version
docker compose config --quiet
docker compose config --services
docker compose ps
df -h .
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py check
```

Registrar a versão efetiva da aplicação, imagens, digests, PostgreSQL, Redis/Valkey, plugins, proxy, certificados, autenticação, volumes e serviços adicionais. Não anexar `env`, credenciais ou saída integral de `docker compose config` a chamados: essa saída pode conter segredos.

Uma baseline deve conter contagens por tipo de objeto, amostras de hierarquias, endereços IP, VLANs, cabos, contatos, anexos, permissões e dados de plugins. Contagens iguais ajudam a detectar perdas, mas não comprovam integridade sozinhas.

### 5.2 Compatibilidade e artefatos

Fixar versões exatas e, preferencialmente, digests em um registro corporativo. Revisar o Dockerfile e os arquivos Compose em controle de versão, excluindo segredos. Construir o artefato antes da manutenção e promover a mesma imagem homologada para produção.

Não atualizar PostgreSQL, Redis/Valkey e NetBox simultaneamente por conveniência. Quando a versão de destino exigir mudança de infraestrutura, executar o plano específico de migração dessas dependências, incluindo sua recuperação.

Para plugins, consultar as matrizes dos mantenedores, fixar versões e testar suas migrações e funcionalidades. Ausência de suporte declarado é um impedimento até que haja decisão técnica documentada e homologação adequada.

### 5.3 Ensaio

Restaurar uma cópia do backup em ambiente isolado. Usar credenciais próprias de homologação e bloquear webhooks, e-mails, sincronizações, tarefas agendadas e acesso a destinos de produção. Tratar os dados conforme a política de privacidade da empresa.

Executar o mesmo roteiro de atualização, medir tempos e validar fluxos funcionais. Depois, ensaiar a recuperação para a versão anterior. Registrar tempos, falhas encontradas e ajustes realizados. Listar um dump com `pg_restore --list` não substitui uma restauração real.

## 6. Referência para NetBox 4.7.2

A versão 4.7 requer Python 3.12–3.14, PostgreSQL 15 ou superior e Redis 6 ou superior. O banco precisa permitir a instalação da extensão `ltree`. Confirmar a compatibilidade de Valkey na imagem e na configuração efetivamente adotadas. [Requisitos de atualização](https://github.com/netbox-community/netbox/blob/v4.7.2/docs/installation/upgrading.md).

A mudança para 4.7 altera estruturas hierárquicas e pode aumentar o tempo de migração. O retorno exige restauração do banco anterior, pois a reversão das migrações não recompõe todos os dados históricos. Revisar também os efeitos nas APIs e integrações. [Notas da versão 4.7](https://github.com/netbox-community/netbox/blob/v4.7.2/docs/release-notes/version-4.7.md).

| Item observado na instalação de referência | Valor em 11/10/2026 |
|---|---|
| Diretório | `<DIRETORIO_NETBOX>` |
| Versão anterior | 4.2.9 |
| Versão após atualização | 4.7.2-Docker-5.1.1 |
| Imagem base | `netboxcommunity/netbox:v4.7.2-5.1.1` |
| Imagem personalizada | `netbox-local:4.7.2-plugins` |
| Topology Views | 4.7.0 |
| Floorplan | 0.10.0 |
| PostgreSQL | 17-alpine |
| Redis compatível utilizado | Valkey 8.0-alpine |
| Serviços ativos | netbox, netbox-worker, postgres, redis, redis-cache |

Esses valores são uma referência local, não padrões universais para outras empresas ou futuras versões.

Na transição desta instalação, a imagem passou a usar o usuário `netbox:root`, o healthcheck `/opt/netbox/health.sh` e não inclui `/opt/netbox/housekeeping.sh`. A manutenção é agendada pelo NetBox e atendida pelo worker. Revisar serviços legados antes de removê-los; não chamar `docker compose stop` com um nome ausente da configuração atual.

Preservar `SECRET_KEY`, chaves de autenticação e `API_TOKEN_PEPPERS`. Os peppers permitem verificar os tokens que deles dependem; perda ou substituição sem planejamento pode invalidar o acesso de integrações. Novos ambientes devem armazenar esses valores em mecanismo corporativo de segredos. [Parâmetros obrigatórios](https://netbox.readthedocs.io/en/stable/configuration/required-parameters/).

## 7. Backup final consistente

### 7.1 Congelar escritas

1. Ativar a página de manutenção no proxy ou balanceador e restringir o acesso direto ao backend.
2. Suspender sincronizadores, pipelines, scripts, agendadores e clientes que escrevem via API.
3. Impedir novos trabalhos e aguardar a conclusão dos trabalhos em execução; verificar todas as filas e jobs iniciados.
4. Parar aplicação, workers e outros serviços que escrevam no banco ou arquivos.
5. Manter PostgreSQL disponível para o dump.

No ambiente de referência atual:

```bash
docker compose stop netbox netbox-worker
```

Se houver serviço de manutenção legado, pará-lo também usando o inventário feito antes de alterar o Compose. Em múltiplos hosts, parar todos os escritores. Não prosseguir se houver qualquer escritor ativo.

### 7.2 Criar e verificar o backup

O exemplo pressupõe PostgreSQL no Compose, variáveis `POSTGRES_USER` e `POSTGRES_DB` e os diretórios persistentes usados pela implantação de referência. Executar em uma sessão Bash e manter as variáveis para as etapas seguintes.

```bash
set -euo pipefail
umask 077
CHANGE_ID='CHG-PREENCHER'
BACKUP_DIR="$PWD/backups/${CHANGE_ID}-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# Salvar a configuração antiga antes de editar qualquer arquivo.
cp -a docker-compose.yml docker-compose.override.yml \
  Dockerfile-Plugins plugin_requirements.txt "$BACKUP_DIR/"
cp -a configuration env "$BACKUP_DIR/"
if [ -f .env ]; then cp -a .env "$BACKUP_DIR/"; fi

docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$BACKUP_DIR/database.dump"
test -s "$BACKUP_DIR/database.dump"
docker compose exec -T postgres pg_restore --list \
  < "$BACKUP_DIR/database.dump" > "$BACKUP_DIR/database-contents.txt"

NETBOX_CID="$(docker compose ps -a -q netbox)"
test -n "$NETBOX_CID"
for directory in media reports scripts; do
  docker cp "$NETBOX_CID:/opt/netbox/netbox/$directory" \
    "$BACKUP_DIR/$directory"
done

docker compose images > "$BACKUP_DIR/images.txt"
docker inspect "$NETBOX_CID" \
  --format '{{.Config.Image}} {{.Image}}' > "$BACKUP_DIR/previous-image.txt"
tar -czf "$BACKUP_DIR/persistent-files.tar.gz" \
  -C "$BACKUP_DIR" media reports scripts
(
  cd "$BACKUP_DIR"
  sha256sum database.dump persistent-files.tar.gz > SHA256SUMS
  sha256sum -c SHA256SUMS
)
printf 'Backup final: %s\n' "$BACKUP_DIR"
```

Adaptar a lista para armazenamento externo, diretórios personalizados, certificados, plugins com arquivos próprios, segredos externos e arquivos Compose adicionais. `docker cp` copia os arquivos visíveis no contêiner parado, incluindo os volumes montados; validar permissões e conteúdo no ensaio de restauração.

O dump não inclui automaticamente papéis globais do PostgreSQL. O DBA deve garantir a recuperação dos papéis, privilégios e configurações necessários. Quando aplicável, salvar esses elementos por procedimento específico com acesso restrito.

Copiar o backup para repositório corporativo criptografado, independente do host, conforme retenção aprovada. Confirmar a cópia e seus checksums. Arquivos `env`, configurações e o banco contêm informações sensíveis. Documentar a restauração testada e garantir que o backup final possa ser restaurado antes de migrar.

## 8. Preparar o destino e executar

### 8.1 Construção antecipada

Preparar o Dockerfile e os requisitos em checkout separado antes da janela. Não alterar o conjunto de implantação ativo durante a construção. Para o exemplo 4.7.2:

```dockerfile
FROM netboxcommunity/netbox:v4.7.2-5.1.1
COPY plugin_requirements.txt /opt/netbox/plugin_requirements.txt
RUN /usr/local/bin/uv pip install --python /opt/netbox/venv/bin/python \
    -r /opt/netbox/plugin_requirements.txt
COPY configuration/plugins.py /etc/netbox/config/plugins.py
RUN mkdir -p /opt/netbox/netbox/static/netbox_topology_views/img \
    && SECRET_KEY=build-only-placeholder-key-that-is-long-enough-for-netbox \
    /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py collectstatic --no-input
```

```text
netbox-topology-views==4.7.0
netbox-floorplan-plugin==0.10.0
```

O valor usado no build é apenas um placeholder, não uma chave de produção. Não incorporar segredos reais às camadas da imagem. Esses comandos e caminhos são específicos da imagem indicada. [Construção com plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).

No checkout de preparação, construir a imagem e executar a homologação. Em produção, usar o artefato já aprovado, mantendo a mesma imagem para aplicação e worker. Não usar tags móveis como `latest`.

### 8.2 Aplicação em produção

Depois do backup final, instalar os arquivos de implantação aprovados. Conferir imagens, usuários, comandos, healthchecks, nomes de serviços e mounts, mantendo os volumes corretos do banco e dos arquivos.

```bash
docker compose config --quiet
docker compose config --services

# Iniciar apenas a aplicação para que sua inicialização aplique as migrações.
docker compose up -d --no-build netbox
docker compose logs --timestamps --tail=100 netbox
docker compose ps
```

Na imagem NetBox Docker indicada, o entrypoint executa as migrações e tarefas de preparação ao iniciar a aplicação. Não executar uma segunda migração em paralelo. Workers de versões diferentes devem continuar parados enquanto o esquema muda. [Atualização do NetBox Docker](https://github.com/netbox-community/netbox-docker/wiki/Updating).

Acompanhar logs até o término das migrações, preparação de caches e início do servidor. Ajustar `start_period` e o limite da janela com base no ensaio; healthcheck ainda em inicialização não comprova falha da migração. Se houver erro, registrar o ponto da falha e aplicar a decisão da seção 4.

Depois de a aplicação estar saudável:

```bash
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py migrate --check
docker compose exec -T netbox /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py check
docker compose up -d --no-build netbox-worker
docker compose ps
docker compose logs --timestamps --tail=100 netbox-worker
```

Usar `migrate --check` para verificar pendências, não para executar outra migração. Se houver serviços removidos na versão de destino, tratar os contêineres órfãos explicitamente conforme o inventário; revisar o impacto antes de usar `--remove-orphans`. Não usar `docker compose down -v`, `docker volume rm` ou limpeza de volumes durante o procedimento.

## 9. Validação e liberação

Manter a manutenção e as integrações suspensas até o aceite. Testar também o endereço corporativo pelo proxy, pois HTTP 200 no backend não valida TLS, SSO ou roteamento externo.

| Verificação | Critério de aceite | Evidência |
|---|---|---|
| Versão e artefato | Versão e imagem iguais às homologadas | Versão exibida e digest |
| Migrações | Nenhuma pendência ou falha | Código de saída e logs |
| Diagnóstico Django | Sem erros; avisos avaliados | Saída de `manage.py check` |
| Saúde | Aplicação, worker e dependências saudáveis | `docker compose ps` |
| Autenticação | Login local e SSO/LDAP utilizados funcionam | Teste com contas autorizadas |
| Autorização | Perfil restrito mantém limites esperados | Testes de acesso permitido e negado |
| Dados | Contagens e amostras compatíveis com baseline | Comparação e consultas |
| Hierarquias | Pais e descendentes coerentes | Amostras de regiões, locais e grupos |
| Arquivos e plugins | Anexos, mapas e plantas funcionam | Testes funcionais |
| API | Token existente e operações utilizadas funcionam | Teste dos clientes corporativos |
| Worker | Job controlado concluído; scheduler ativo | Resultado do job e logs |
| Integrações | Fluxo representativo aprovado pelos responsáveis | Resultado da homologação operacional |
| Desempenho | Tempos e erros dentro dos limites registrados | Métricas comparadas à baseline |

Executar escritas de teste apenas em objetos de validação acordados, com limpeza e rastreabilidade. Não usar objetos reais de produção para testes destrutivos.

Após o aceite, retirar a manutenção, retomar integrações gradualmente e observar filas, erros HTTP, latência, CPU, memória, conexões do banco e falhas de autenticação. Definir na mudança a duração dessa observação e os limiares que motivam intervenção.

## 10. Rollback por restauração

### 10.1 Princípio

Recuperar um conjunto coerente: **imagem anterior + configuração anterior + banco anterior + arquivos anteriores + segredos correspondentes**. Trocar somente a tag da imagem não restaura o esquema do banco.

O rollback descarta, no banco recuperado, alterações posteriores ao backup final. Se houver escritas após a liberação, o responsável pelo serviço deve avaliar a perda e um plano de reconciliação antes da restauração.

### 10.2 Sequência operacional

1. Reativar manutenção, bloquear escritores e parar aplicação e workers em todos os hosts.
2. Preservar logs e, se viável dentro do RTO, uma cópia do estado com falha para investigação.
3. Validar checksums e identificar exatamente o backup aprovado.
4. Restaurar os arquivos de implantação antigos, segredos e permissões. Remover ou reconciliar arquivos novos que não existiam na versão anterior, mediante revisão.
5. Recuperar o banco em uma base vazia preparada pelo DBA e restaurar os arquivos persistentes.
6. Iniciar a aplicação com a imagem anterior, validar e somente depois iniciar os workers.
7. Repetir os testes de aceite, liberar acessos e registrar a recuperação.

Preferir restauração em uma base ou volume separado, preservando o estado com falha até encerrar a análise. No Compose de referência, o volume PostgreSQL contém a base; não substituí-lo por um volume vazio sem planejar a criação dos papéis e do banco.

Exemplo de restauração **após o DBA preparar uma base vazia e autorizar sua substituição**. As variáveis devem apontar para o ambiente de recuperação, nunca ser copiadas sem conferência:

```bash
set -euo pipefail
umask 077
: "${BACKUP_DIR:?Defina o caminho absoluto do backup aprovado}"
(
  cd "$BACKUP_DIR"
  sha256sum -c SHA256SUMS
)

# O serviço postgres deve estar configurado para a base vazia de recuperação.
# POSTGRES_DB e POSTGRES_USER devem corresponder ao destino preparado pelo DBA.
docker compose exec -T postgres sh -c \
  'pg_restore --exit-on-error --single-transaction \
   -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < "$BACKUP_DIR/database.dump"
```

Esse comando não cria uma base vazia nem elimina objetos existentes. Não aplicar sobre o banco parcialmente migrado. Se a organização preferir recriar a base original, a terminação de conexões e a exclusão da base devem constar em procedimento DBA específico e autorizado.

Restaurar `media`, `reports` e `scripts` nos volumes corretos usando um contêiner auxiliar aprovado ou o mecanismo corporativo de backup. Validar proprietário, permissões e conteúdo; copiar por cima pode deixar arquivos novos residuais. O procedimento exato deve ser ensaiado conforme o armazenamento adotado.

Restaurar também a coerência das filas: não iniciar o worker antigo com jobs criados por código novo. Definir no plano se os jobs serão preservados, reconstituídos ou cancelados, com avaliação do responsável. Não limpar Redis/Valkey indiscriminadamente.

## 11. Encerramento e evidências

Anexar à mudança, em repositório de acesso restrito:

- Aprovação, horários reais, indisponibilidade e responsáveis.
- Versões, digests e revisão dos arquivos de implantação.
- Identificação do backup, checksums e comprovação de restauração.
- Logs de migração, verificações internas e testes funcionais.
- Comparação da baseline e aceite das integrações.
- Resultado da observação, incidentes e decisão de concluir ou reverter.

Atualizar inventário/CMDB, documentação, monitoração e procedimento de recuperação. Preservar backup e imagem anterior conforme retenção aprovada; só removê-los quando expirar o período definido e houver autorização operacional aplicável.

## 12. Adaptação a outras arquiteturas

| Arquitetura | Ajustes necessários |
|---|---|
| Git ou arquivo de distribuição | Manter o método original; preparar nova versão, configuração e dependências; executar `upgrade.sh` e reiniciar os serviços definidos na instalação |
| Kubernetes | Fixar imagem, controlar réplicas e escritores; executar migrações por mecanismo exclusivo; validar PVCs, segredos, probes e estratégia de recuperação |
| Vários hosts/alta disponibilidade | Bloquear todas as réplicas e workers; impedir mistura de versões durante a migração; controlar tráfego pelo balanceador |
| PostgreSQL gerenciado | Usar backup lógico e/ou snapshot conforme serviço; ensaiar restauração, permissões e extensão necessária |
| Arquivos em armazenamento de objetos | Preservar versões e consistência do conteúdo com o banco; incluir política de recuperação dos objetos |

O comando `upgrade.sh` pertence à instalação por Git/arquivo e não deve ser acrescentado ao fluxo Docker acima. A instalação via pacote Python é experimental na versão 4.7 e não é a referência deste procedimento. [Métodos oficiais de atualização](https://github.com/netbox-community/netbox/blob/v4.7.2/docs/installation/upgrading.md).

## 13. Registro da atualização local de 11/10/2026

A instalação em `<DIRETORIO_NETBOX>` foi atualizada de 4.2.9 para 4.7.2. As verificações realizadas registraram zero migrações pendentes, diagnóstico interno sem problemas, aplicação e worker saudáveis e login local com HTTP 200. As contagens conferidas permaneceram em 10 dispositivos, 1 site, 1 rack, 0 máquinas virtuais e 1 usuário.

Backup: `<DIRETORIO_NETBOX>/backups/pre-4.7.2-20261011-102716`.

Registro técnico: `<DIRETORIO_NETBOX>/ATUALIZACAO-4.7.2.md`.

O arquivo de backup foi listado com `pg_restore --list`. Não há, no registro desta execução, evidência de restauração integral em homologação, teste de SSO, teste funcional autenticado dos plugins ou aceite de todas as integrações. Esses controles permanecem necessários para futuras mudanças conduzidas segundo este procedimento corporativo.

## 14. Referências oficiais e manutenção do documento

Fontes consultadas em 11/10/2026:

1. [NetBox — atualização, referência fixada em 4.7.2](https://github.com/netbox-community/netbox/blob/v4.7.2/docs/installation/upgrading.md).
2. [NetBox — documentação de atualização vigente](https://netbox.readthedocs.io/en/stable/installation/upgrading/).
3. [NetBox — notas da versão 4.7](https://github.com/netbox-community/netbox/blob/v4.7.2/docs/release-notes/version-4.7.md).
4. [NetBox Docker — atualização](https://github.com/netbox-community/netbox-docker/wiki/Updating).
5. [NetBox Docker — uso de plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).
6. [NetBox — parâmetros obrigatórios e segredos](https://netbox.readthedocs.io/en/stable/configuration/required-parameters/) e [configuração de segurança](https://netbox.readthedocs.io/en/stable/configuration/security/).
7. [Topology Views — configuração da versão 4.7.0](https://github.com/netbox-community/netbox-topology-views/blob/v4.7.0/netbox_topology_views/__init__.py).
8. [Floorplan — matriz de compatibilidade](https://github.com/netbox-community/netbox-floorplan-plugin/blob/main/COMPATIBILITY.md).

Antes de cada mudança, revisar as fontes correspondentes à versão de destino. Páginas `stable`, branches e wikis podem mudar. Arquivar a revisão consultada e atualizar este documento quando houver alteração de versão, arquitetura, armazenamento ou requisitos de recuperação.

| Histórico | Alteração |
|---|---|
| 1.0 — 11/10/2026 | Procedimento inicial com fluxo Docker, controles corporativos e referência local 4.7.2 |
