# Instalação e testes

## Ambiente

Python 3.10 ou superior, Bash e flock (util-linux). Runtime usa requests; pytest é usado na validação. Dependências têm intervalos controlados em requirements.txt.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp imc/.env.example imc/.env
chmod 600 imc/.env
```

Preencha o arquivo localmente. Exemplos são fictícios e placeholders são rejeitados. Não compartilhe o conteúdo do .env.

Use HTTPS e validação TLS. Configure IMC_CA_BUNDLE e NETBOX_CA_BUNDLE para CA interna. Não é permitido desativar a validação TLS. HTTP só é aceito por configuração explícita e gera aviso. Portas incompatíveis com o protocolo são rejeitadas.

NETBOX_URL deve conter apenas a origem, sem /api. IMC_HOST deve ser hostname ou IPv4 sem protocolo/porta. IMC_PORT padrão HTTPS: 8443. Valores com espaços exigem aspas. Variáveis já presentes no ambiente têm precedência; IMC_ENV_FILE permite escolher outro arquivo. O arquivo não é executado como Bash.

## Validação local sem laboratório

```bash
source .venv/bin/activate
pytest -v
python3 -m compileall .
bash -n imc/executar_sincronizacao.sh
bash -n imc/instalar_cron.sh
bash -n imc/desinstalar_cron.sh
python3 -m unittest discover -s tests -v
python3 scripts/mock_dry_run.py
python3 scripts/audit_security.py
git diff --check
```

A suíte usa apenas mocks. O exemplo mockado bloqueia qualquer tentativa de rede. A auditoria consulta somente arquivos e histórico Git local, apresentando metadados sem valores sensíveis.

`bash -n imc/*.sh` é a verificação solicitada, mas o Bash analisa somente o primeiro arquivo como script; executar também cada arquivo individualmente, como acima.

## Validação manual no laboratório — depende de autorização operacional

Rotacione primeiro a credencial iMC exposta. Configure contas com privilégio mínimo. Confirme endpoints, paginação, nomenclatura e representação de VLANs na versão instalada.

```bash
source .venv/bin/activate
python3 sincronizacao_imc_netbox.py --dry-run
python3 sincronizacao_imc_netbox.py --apply
```

Confira o plano antes de responder SIM. Para execução por wrapper:

```bash
IMC_PYTHON_BIN="$PWD/.venv/bin/python" bash imc/executar_sincronizacao.sh --dry-run
```

Apenas após validação poderá ser usada a opção explícita `--apply --non-interactive`. O instalador cron permanece desativado no piloto. O script `imc/testar_conexao_imc.py` também é manual, usa GET e não imprime inventário; ele valida a configuração completa antes da consulta.

Consulte [contrato](SINCRONIZACAO_IMC_NETBOX.md) e [segurança](docs/SEGURANCA.md).
