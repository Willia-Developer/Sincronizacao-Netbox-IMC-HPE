# Instalação e operação - WhatsUp Gold -> NetBox

## Preparar sem alterar pacotes do sistema

Linux e Python 3.10+ com venv e pip disponíveis. Não é necessário `apt update` para executar este projeto. Caso falte um requisito do sistema, solicite sua instalação ao responsável pelo servidor.

Na raiz do projeto:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
test -f config/wug.json || cp config/wug.example.json config/wug.json
chmod 600 .env config/wug.json
```

Não copie uma venv de outro servidor. Não execute `source .env`. O carregador lê valores como dados e não executa comandos. A venv pode ser ativada, mas os exemplos usam seu Python por caminho explícito.

## Configurar

Em `.env`: WUG_URL, WUG_TOKEN ou WUG_USERNAME/WUG_PASSWORD, NETBOX_URL e NETBOX_TOKEN. Não inclua `/api` nas URLs. Use HTTPS e, quando necessário, configure WUG_CA_BUNDLE/NETBOX_CA_BUNDLE. Validação TLS não pode ser desativada. HTTPS_PROXY_URL é opcional; proxies herdados e .netrc não são usados.

NETBOX_VLAN_GROUP_ID restringe a resolução de VID a um grupo do NetBox. Sem grupo, o VID deve ser único globalmente. O projeto não escolhe o grupo/site por aproximação.

## Validar por etapas

1. `python -m wug check-wug`: autentica e consulta produto. Não altera inventário.
2. `python -m wug list-devices`: lê todas as páginas do grupo configurado. Confira IDs e nomes.
3. `python -m wug check-netbox`: consulta devices, interfaces e VLANs. Não testa PATCH.
4. Complete o perfil local conforme [CONTRATO_API_WUG](docs/CONTRATO_API_WUG.md).
5. `python -m wug inspect --device "SW-LAB-01"`: confira nomes, descrição e VLAN com o switch.
6. `python -m wug sync --device "SW-LAB-01" --dry-run`: examine logs e JSON de alterações.
7. Registre homologação do perfil. Execute `python -m wug sync --device "SW-LAB-01" --apply` e confira novamente o plano antes de responder SIM.
8. Verifique o inventário NetBox e repita o dry-run. Não deve propor novamente os campos já confirmados e inalterados na fonte.

Todos os comandos devem usar `.venv/bin/python` quando a venv não estiver ativada. `--profile CAMINHO` permite um perfil alternativo, útil para ambientes distintos.

## Falhas comuns

- Perfil sem endpoint de interface: consulte o Swagger instalado; não reutilize cegamente um endpoint de interface de polling IP.
- 401/403 WUG: conta/token/permissão incorretos. Um token expirado interrompe a coleta; não há renovação automática nesta versão.
- Falha TLS: forneça a CA correta. Não use verificação desativada.
- Interface ausente: confira nome exato ou mapeamento por ID de origem no perfil.
- VLAN ambígua: confira grupo de VLAN; associações são preservadas.
- Plano com erros: nenhuma aplicação começa; resolva os erros e gere novo plano.
- PATCH incerto: confira estado `sending`/`unconfirmed`, origem e NetBox antes de repetir a execução.

## Produção

Comece com grupo restrito e simulação. Use `--all-devices` somente depois de validar cobertura e permissões. `--max-changes` limita quantidade de interfaces, não quantidade de campos. Cada execução é única, sem agendamento automático.

O wrapper `scripts/executar_sincronizacao.sh` aceita os argumentos de sync. Configure SYNC_PYTHON_BIN com caminho da venv. Ele não carrega credenciais como shell.

## Testes offline

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate.py
```

Resultado agregado em artifacts/validation.json. Testes offline não comprovam disponibilidade de campos na versão instalada.
