# Instalação do NetBox 4.2.9 com Topology Views e Floorplan

> Documento histórico da instalação 4.2.9. O ambiente atual usa 4.7.2 com oito plugins. Consulte o [passo a passo atualizado](MANUTENCAO-NETBOX-E-PLUGINS.md) para instalação dos plugins e atualização do NetBox.

Este documento registra o procedimento executado em 9 de outubro de 2026 no computador `<SERVIDOR>`, desde a inspeção inicial até a liberação e validação do acesso pelo Tailscale. Os comandos de criação de credenciais são destinados a uma instalação nova; não devem ser repetidos em uma instalação com dados existentes.

## 1. Resultado final

| Componente | Versão ou configuração |
|---|---|
| Sistema | Ubuntu, arquitetura x86_64 |
| Usuário do sistema | `<USUARIO>` |
| Docker Engine existente | 29.1.3 |
| Docker Compose instalado | 2.39.4 |
| Repositório de configuração | `netbox-community/netbox-docker`, tag `3.2.1` |
| Commit do repositório | `2efacf39ca0f885ebaca27fdf7d7fb9fc5241c51` |
| NetBox | 4.2.9 |
| Imagem base | `netboxcommunity/netbox:v4.2.9-3.2.1` |
| Imagem construída | `netbox-local:4.2.9-plugins` |
| Topology Views | 4.2.1 |
| Floorplan | 0.6.0 |
| Banco | PostgreSQL, imagem `postgres:17-alpine` |
| Filas e cache | Valkey, imagem `valkey/valkey:8.0-alpine` |
| Diretório | `<DIRETORIO_NETBOX>` |
| Acesso local | <http://localhost:8080> |
| Acesso Tailscale | `http://<IP_TAILSCALE>:8080` |
| Administrador | `admin` |

A senha administrativa está em `<DIRETORIO_NETBOX>/admin-credentials.txt`, com permissão `600`. As senhas e a chave de aplicação não são reproduzidas neste documento.

## 2. Inspeção inicial do ambiente

Foram verificados usuário, sistema operacional, Docker, containers existentes, possíveis instalações do NetBox e portas em uso:

```bash
pwd
id
uname -a
command -v docker
docker version
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
docker compose version
command -v docker-compose
ls -ld /opt/netbox
ss -ltn
```

Resultados relevantes:

- Docker já instalado; o usuário `<USUARIO>` pertence ao grupo `docker`.
- Não havia containers Docker existentes.
- Não havia instalação em `/opt/netbox`.
- O comando `docker compose` ainda não estava disponível.
- A porta 8080 estava disponível; outras aplicações já usavam portas como 80, 3000 e 8000.

Por isso, foi utilizada uma instalação Docker no diretório do usuário, com porta 8080. Não foi necessário instalar o Docker Engine.

O sandbox da sessão falhou com `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Os comandos de sistema necessários foram então executados com autorização fora do sandbox. Essa falha era da execução da sessão, não do NetBox.

## 3. Seleção das versões dos plugins

Foram consultadas as fontes dos projetos:

- [Topology Views: instalação e tabela de versões](https://github.com/netbox-community/netbox-topology-views).
- [Manifesto do Topology Views 4.2.1](https://github.com/netbox-community/netbox-topology-views/blob/v4.2.1/netbox_topology_views/__init__.py).
- [Matriz de compatibilidade do Floorplan](https://github.com/netbox-community/netbox-floorplan-plugin/blob/master/COMPATIBILITY.md).
- [Manifesto do Floorplan 0.6.0](https://github.com/netbox-community/netbox-floorplan-plugin/blob/0.6.0/netbox_floorplan/__init__.py).

Foi escolhido Floorplan 0.6.0, cuja matriz indica NetBox 4.2.x e cujo manifesto aceita de 4.2.0 até 4.2.99. Foi escolhido Topology Views 4.2.1; a tabela do projeto cita NetBox 4.2.1, e seu funcionamento no NetBox 4.2.9 foi verificado nesta instalação por carregamento, migrações e acesso autenticado às páginas. A verificação não incluiu uma topologia preenchida com dispositivos e cabos.

As versões foram fixadas para impedir que uma reconstrução instale automaticamente releases de plugins destinadas a versões mais recentes do NetBox.

## 4. Download da configuração oficial

```bash
git clone --branch 3.2.1 --depth 1 \
  https://github.com/netbox-community/netbox-docker.git \
  <DIRETORIO_NETBOX>

cd <DIRETORIO_NETBOX>
```

O checkout da tag ficou em `detached HEAD`, comportamento normal ao clonar uma tag.

O repositório fornece `docker-compose.yml`, arquivos `env/*.env`, configuração da aplicação e comandos de inicialização, migração e manutenção.

## 5. Instalação do Docker Compose no diretório do usuário

```bash
mkdir -p ~/.docker/cli-plugins

curl -fL \
  https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64 \
  -o ~/.docker/cli-plugins/docker-compose

chmod +x ~/.docker/cli-plugins/docker-compose
docker compose version
```

Resultado: `Docker Compose version v2.39.4`.

## 6. Confirmação da imagem do NetBox

Foi confirmada a existência da tag exata:

```bash
docker manifest inspect netboxcommunity/netbox:v4.2.9-3.2.1 >/dev/null
```

A imagem utilizada na construção foi resolvida para o digest:

```text
sha256:7bf0eb72ba8079ebbc053f0d324654b3482bafde2f34ff07fa6777533171c337
```

## 7. Definição dos pacotes dos plugins

Foi criado `<DIRETORIO_NETBOX>/plugin_requirements.txt`:

```text
netbox-topology-views==4.2.1
netbox-floorplan-plugin==0.6.0
```

## 8. Ativação dos plugins

Foi editado `configuration/plugins.py`. As configurações efetivas são:

```python
PLUGINS = ["netbox_topology_views", "netbox_floorplan"]

PLUGINS_CONFIG = {
    "netbox_topology_views": {
        "allow_coordinates_saving": True,
    },
}
```

O salvamento de coordenadas do Topology Views foi habilitado para permitir posicionar dispositivos na visualização. O Floorplan foi ativado com suas configurações padrão.

## 9. Construção de uma imagem com os plugins

Foi criado `Dockerfile-Plugins`:

```dockerfile
FROM netboxcommunity/netbox:v4.2.9-3.2.1
COPY plugin_requirements.txt /opt/netbox/plugin_requirements.txt
RUN /usr/local/bin/uv pip install --python /opt/netbox/venv/bin/python -r /opt/netbox/plugin_requirements.txt
COPY configuration/plugins.py /etc/netbox/config/plugins.py
RUN mkdir -p /opt/netbox/netbox/static/netbox_topology_views/img && SECRET_KEY=build-only-placeholder-key-that-is-long-enough-for-netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py collectstatic --no-input
```

Esse arquivo instala os plugins no ambiente virtual da imagem oficial e coleta seus arquivos estáticos. A `SECRET_KEY` nessa instrução é apenas um valor temporário para a etapa de construção; em execução, a aplicação usa a chave privada definida em `env/netbox.env`.

## 10. Configuração inicial do Compose

Foi criado `docker-compose.override.yml`, aplicado automaticamente pelo Compose junto com `docker-compose.yml`.

Inicialmente, a publicação da porta era apenas:

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

O serviço principal recebeu a configuração de construção. NetBox, worker e housekeeping passaram a usar `netbox-local:4.2.9-plugins`. Todos os seis serviços receberam `restart: unless-stopped`.

O arquivo final completo, incluindo o ajuste posterior do Tailscale e do tempo de saúde, está na seção 15.

## 11. Geração de senhas privadas para os serviços

As senhas de exemplo do repositório foram substituídas por valores aleatórios. O banco e o NetBox receberam a mesma senha de banco; cada serviço Valkey recebeu sua própria senha, correspondente à configuração do NetBox.

Este foi o procedimento usado, destinado somente à instalação inicial:

```bash
cd <DIRETORIO_NETBOX>

python3 - <<'PY'
from pathlib import Path
import secrets

root = Path('<DIRETORIO_NETBOX>')
values = {
    'DB_PASSWORD': secrets.token_hex(24),
    'REDIS_PASSWORD': secrets.token_hex(24),
    'REDIS_CACHE_PASSWORD': secrets.token_hex(24),
    'SECRET_KEY': secrets.token_hex(50),
}

p = root / 'env/netbox.env'
s = p.read_text()
for key, value in values.items():
    s = '\n'.join(
        key + '=' + value if line.startswith(key + '=') else line
        for line in s.split('\n')
    )
s += '\nALLOWED_HOSTS=localhost 127.0.0.1\nCORS_ORIGIN_ALLOW_ALL=False\n'
p.write_text(s)

for filename, key, target in [
    ('postgres.env', 'DB_PASSWORD', 'POSTGRES_PASSWORD'),
    ('redis.env', 'REDIS_PASSWORD', 'REDIS_PASSWORD'),
    ('redis-cache.env', 'REDIS_CACHE_PASSWORD', 'REDIS_PASSWORD'),
]:
    p = root / 'env' / filename
    p.write_text('\n'.join(
        target + '=' + values[key] if line.startswith(target + '=') else line
        for line in p.read_text().split('\n')
    ))

for p in (root / 'env').glob('*.env'):
    p.chmod(0o600)

print('Credenciais dos serviços geradas.')
PY
```

O arquivo original tinha `CORS_ORIGIN_ALLOW_ALL=True`; foi acrescentado `CORS_ORIGIN_ALLOW_ALL=False` ao fim, que é o valor efetivo carregado. `SKIP_SUPERUSER=true` foi mantido, pois o administrador seria criado explicitamente depois.

Não repita esse script com o banco já inicializado: alterar somente `POSTGRES_PASSWORD` no arquivo não altera a senha do usuário dentro de um banco existente.

## 12. Construção e primeira inicialização

```bash
cd <DIRETORIO_NETBOX>
docker compose build netbox
docker compose up -d
```

A construção instalou os dois pacotes com as versões fixadas. O `collectstatic` informou 60 arquivos copiados e 502 inalterados.

O Compose criou a rede `netbox_default`, os containers e os volumes persistentes. A inicialização oficial da imagem aplicou as migrações, inclusive as dos plugins; não foi necessário executar uma instalação separada por `pip` dentro de um container em execução.

Na primeira inicialização, as migrações demoraram mais que o tempo de saúde inicial. O primeiro `up -d` terminou com `dependency failed to start: container netbox-netbox-1 is unhealthy`. Depois de a aplicação ficar pronta, foi executado novamente:

```bash
docker compose up -d
```

Isso iniciou worker e housekeeping. O `start_period` do serviço principal foi posteriormente ampliado para `300s` para acomodar inicializações com migrações.

## 13. Criação do administrador

Foi gerada uma senha aleatória e criado o usuário `admin` pelo Django. O arquivo de credenciais foi gravado com permissão `600`.

Procedimento executado, destinado à criação inicial do usuário:

```bash
cd <DIRETORIO_NETBOX>

python3 - <<'PY'
import secrets
import subprocess
from pathlib import Path

password = secrets.token_urlsafe(24)
p = Path('admin-credentials.txt')
p.touch(mode=0o600)
p.chmod(0o600)
p.write_text(
    'Usuario: admin\nSenha: ' + password +
    '\nURL: http://localhost:8080\n'
)

code = (
    'from django.contrib.auth import get_user_model; '
    'u=get_user_model().objects.create_superuser('
    'username="admin",email="admin@localhost",password=' +
    repr(password) + '); print("Administrador criado.")'
)
subprocess.run([
    'docker', 'compose', 'exec', '-T', 'netbox',
    '/opt/netbox/venv/bin/python',
    '/opt/netbox/netbox/manage.py', 'shell', '-c', code,
], check=True)
PY
```

Para consultar a senha no terminal local:

```bash
cat <DIRETORIO_NETBOX>/admin-credentials.txt
```

Não repita o script de criação se `admin` já existir. Para trocar sua senha, use:

```bash
docker compose exec netbox \
  /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py changepassword admin
```

Depois de uma troca manual, a senha antiga do arquivo de credenciais deixa de ser válida.

## 14. Verificações da instalação local

Foi executado o diagnóstico Django:

```bash
docker compose exec -T netbox \
  /opt/netbox/venv/bin/python \
  /opt/netbox/netbox/manage.py check
```

Resultado: `System check identified no issues (0 silenced).`

Também foram verificados:

- Login autenticado com o usuário `admin`.
- Páginas dos plugins retornando HTTP 200.
- Endpoint `/api/status/` após autenticação.
- Saúde dos serviços com `docker compose ps`.

O status retornou:

```json
{
  "netbox-version": "4.2.9-Docker-3.2.1",
  "plugins": {
    "netbox_floorplan": "0.6.0",
    "netbox_topology_views": "4.2.1"
  }
}
```

Um teste inicialmente comparou a versão inteira com `4.2.9` e falhou por causa do sufixo Docker. A comparação foi corrigida para considerar a parte anterior ao primeiro hífen, confirmando a versão solicitada.

## 15. Diagnóstico e habilitação do Tailscale

Depois da instalação local, foi solicitado verificar o acesso por Tailscale:

```bash
tailscale ip -4
ss -ltn '( sport = :8080 )'
curl --connect-timeout 5 --max-time 10 \
  -sS -o /dev/null -w 'HTTP via Tailscale: %{http_code}\n' \
  http://<IP_TAILSCALE>:8080/login/
```

O IP retornado foi `<IP_TAILSCALE>`. O teste falhou porque o Docker publicava a porta somente em `127.0.0.1`.

Após a solicitação para ajustar, foi acrescentado o IP do Tailscale à publicação de portas e aos hosts permitidos. O arquivo final `docker-compose.override.yml` é:

```yaml
services:
  netbox:
    image: netbox-local:4.2.9-plugins
    build:
      context: .
      dockerfile: Dockerfile-Plugins
    ports:
      - "127.0.0.1:8080:8080"
      - "<IP_TAILSCALE>:8080:8080"
    restart: unless-stopped
    healthcheck:
      start_period: 300s
  netbox-worker:
    image: netbox-local:4.2.9-plugins
    restart: unless-stopped
  netbox-housekeeping:
    image: netbox-local:4.2.9-plugins
    restart: unless-stopped
  postgres:
    restart: unless-stopped
  redis:
    restart: unless-stopped
  redis-cache:
    restart: unless-stopped
```

Em `env/netbox.env`, a linha foi alterada para:

```dotenv
ALLOWED_HOSTS=localhost 127.0.0.1 <IP_TAILSCALE>
```

Não foi necessário adicionar `CSRF_TRUSTED_ORIGINS`: o acesso foi direto, usando a mesma origem no formulário e no POST, e o login com proteção CSRF passou no teste.

As alterações foram aplicadas com:

```bash
cd <DIRETORIO_NETBOX>
docker compose up -d
```

O Compose recriou NetBox, worker e housekeeping para carregar a configuração. Um primeiro teste encontrou conexão recusada enquanto a aplicação ainda inicializava; o teste foi repetido depois da inicialização e passou.

## 16. Teste autenticado pelo IP do Tailscale

Este script reproduz a verificação final sem mostrar a senha:

```bash
cd <DIRETORIO_NETBOX>

python3 - <<'PY'
import re
import requests
from pathlib import Path

base = 'http://<IP_TAILSCALE>:8080'
session = requests.Session()

response = session.get(base + '/login/', timeout=30)
response.raise_for_status()
print('Login via IP Tailscale:', response.status_code)

csrf = re.search(
    r'name="csrfmiddlewaretoken" value="([^"]+)"',
    response.text,
).group(1)
password = Path('admin-credentials.txt').read_text().split('Senha: ')[1].splitlines()[0]

response = session.post(
    base + '/login/',
    data={
        'username': 'admin',
        'password': password,
        'csrfmiddlewaretoken': csrf,
    },
    headers={'Referer': base + '/login/'},
    timeout=30,
)
response.raise_for_status()
assert '/logout/' in response.text
print('Autenticacao via IP Tailscale: OK')

for path in [
    '/plugins/netbox_topology_views/topology/',
    '/plugins/floorplan/floorplans/floorplanimages/',
]:
    response = session.get(base + path, timeout=30)
    response.raise_for_status()
    print(path, response.status_code)

response = session.get(base + '/api/status/', timeout=30)
response.raise_for_status()
status = response.json()
assert status['netbox-version'].split('-')[0] == '4.2.9'
assert status['plugins']['netbox_topology_views'] == '4.2.1'
assert status['plugins']['netbox_floorplan'] == '0.6.0'
print('Versoes verificadas: OK')
PY
```

Os testes executados retornaram HTTP 200 na página de login, autenticação bem-sucedida e HTTP 200 nas páginas de Topology Views e Floorplan. O teste foi realizado no próprio servidor usando seu IP do Tailscale; não foi feito a partir de um segundo dispositivo da rede Tailscale. O acesso de outro dispositivo também depende da conexão e das regras de acesso do Tailscale.

Na conferência final, todos os seis serviços estavam `healthy`.

## 17. Acesso e uso dos plugins

No servidor, abra <http://localhost:8080>. Em um dispositivo com acesso autorizado pela rede Tailscale, abra `http://<IP_TAILSCALE>:8080`. Entre com `admin` e a senha do arquivo privado.

### Topology Views

Acesse **Plugins → Topology Views** ou:

```text
http://<IP_TAILSCALE>:8080/plugins/netbox_topology_views/topology/
```

Cadastre dispositivos, interfaces e cabos no NetBox para formar a topologia. As conexões visualizadas dependem desses registros. O salvamento de coordenadas está habilitado.

### Floorplan

Acesse o menu **Plugins → Floorplan**. A página de imagens validada foi:

```text
http://<IP_TAILSCALE>:8080/plugins/floorplan/floorplans/floorplanimages/
```

Cadastre sites, locais e racks, e configure as plantas e posições conforme sua estrutura física. A instalação não incluiu importação de inventário, imagens de plantas ou posicionamento de racks.

## 18. Persistência dos dados

O Compose oficial criou estes volumes:

| Volume | Conteúdo |
|---|---|
| `netbox_netbox-postgres-data` | Banco de dados |
| `netbox_netbox-media-files` | Arquivos de mídia |
| `netbox_netbox-reports-files` | Relatórios |
| `netbox_netbox-scripts-files` | Scripts |
| `netbox_netbox-redis-data` | Dados de filas Valkey |
| `netbox_netbox-redis-cache-data` | Cache Valkey |

Recriar containers preserva esses volumes. `docker compose down -v` remove os volumes e os dados; não use esse comando para uma parada normal.

## 19. Operação cotidiana

Execute no diretório da instalação:

```bash
cd <DIRETORIO_NETBOX>
```

| Objetivo | Comando |
|---|---|
| Iniciar ou aplicar alterações | `docker compose up -d` |
| Parar preservando dados | `docker compose stop` |
| Consultar saúde e portas | `docker compose ps` |
| Consultar logs da aplicação | `docker compose logs --tail=100 netbox` |
| Acompanhar logs | `docker compose logs -f netbox` |
| Consultar logs do worker | `docker compose logs --tail=100 netbox-worker` |
| Reconstruir imagem | `docker compose build netbox` |
| Reiniciar os processos da aplicação | `docker compose restart netbox netbox-worker netbox-housekeeping` |

Depois de alterar arquivos `env/*.env` ou a publicação de portas, use `docker compose up -d` para recriar os serviços afetados; um simples `restart` não carrega novos valores de ambiente.

Os serviços têm `restart: unless-stopped`, portanto reiniciam com o Docker, exceto se tiverem sido explicitamente parados. Como a porta está vinculada ao IP do Tailscale, esse endereço precisa estar disponível no host para o Docker publicar a porta.

## 20. Arquivos entregues

| Arquivo | Finalidade |
|---|---|
| `docker-compose.yml` | Base oficial dos serviços e volumes |
| `docker-compose.override.yml` | Imagem com plugins, portas e reinício |
| `Dockerfile-Plugins` | Construção da imagem customizada |
| `plugin_requirements.txt` | Versões fixadas dos plugins |
| `configuration/plugins.py` | Ativação e configuração dos plugins |
| `env/netbox.env` | Configuração e credenciais privadas da aplicação |
| `env/postgres.env` | Credenciais do banco |
| `env/redis.env` | Credenciais das filas |
| `env/redis-cache.env` | Credenciais do cache |
| `admin-credentials.txt` | Usuário e senha administrativa |
| `INSTALACAO.md` | Guia breve de operação |
| `PASSO_A_PASSO_COMPLETO.md` | Este registro completo |

## 21. Escopo concluído

Foram concluídos instalação, ativação dos dois plugins, coleta de arquivos estáticos, migrações, criação do administrador, configuração de persistência e reinício, acesso local e publicação pelo IP do Tailscale. Login, páginas dos plugins, versões e saúde dos serviços foram verificados.

Não foram configurados domínio, proxy reverso ou HTTPS, nem importados dispositivos, cabos, racks ou plantas. O endereço publicado utiliza HTTP na porta 8080 sobre a interface do Tailscale.
