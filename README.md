# WhatsUp Gold -> NetBox

Integração unidirecional de inventário. O WhatsUp Gold é a fonte consultada; o script compara os valores e atualiza somente descrição e associações de VLAN de interfaces existentes no NetBox. O NetBox nunca envia alterações ao WhatsUp Gold.

## Estado da entrega

Código implementado e validado com testes offline. Não homologado nas APIs da empresa. O perfil distribuído permite configurar autenticação e descoberta, mas deixa o endpoint de portas físicas em branco e a aplicação desabilitada até a validação local. Não é suficiente renomear uma URL do IMC.

A autenticação pode usar POST exclusivamente em `/api/v1/token`; isso obtém uma sessão e não autoriza alteração de inventário. Todas as consultas WUG usam GET. PUT, PATCH, DELETE e POST em recursos de inventário WUG são bloqueados antes do transporte.

## Começar

Use Python 3.10+ em Linux. A instalação é isolada em ambiente virtual; não exige atualizar pacotes do servidor.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
test -f config/wug.json || cp config/wug.example.json config/wug.json
chmod 600 .env config/wug.json
```

Edite os dois arquivos localmente. Não execute `.env` como shell. Configure URLs HTTPS reais, credenciais e CA interna quando necessária. Valores exportados no terminal prevalecem sobre `.env`. `SYNC_ENV_FILE` seleciona outro arquivo de ambiente.

```bash
.venv/bin/python -m wug check-wug
.venv/bin/python -m wug list-devices
.venv/bin/python -m wug check-netbox
```

Antes dos próximos comandos, complete o mapeamento de portas físicas conforme [o contrato da API](docs/CONTRATO_API_WUG.md). O exemplo não inventa campos de VLAN nem identifica comentário de monitor como descrição administrativa.

```bash
.venv/bin/python -m wug inspect --device "SW-LAB-01"
.venv/bin/python -m wug sync --device "SW-LAB-01" --dry-run
```

Revise logs e o relatório JSON em `relatorios/`. Para habilitar aplicação, homologue o perfil com amostras reais e preencha `validated`, `product_version`, `validated_by`, `validated_at` e `evidence`. A declaração local não substitui a conferência operacional.

```bash
.venv/bin/python -m wug sync --device "SW-LAB-01" --apply
```

O comando recalcula um plano, persiste valores anteriores/propostos e solicita `SIM`. Não aplica automaticamente um relatório antigo. O limite padrão é 100 interfaces por execução; acima dele nenhuma escrita começa. `--max-changes N` altera esse limite explicitamente.

## Regras principais

- Dispositivos e interfaces são associados por nome exato, com mapeamentos explícitos opcionais. Duplicidades bloqueiam o lote de aplicação.
- Objetos ausentes não são criados. Nenhum objeto é excluído. VLANs precisam existir no NetBox.
- Campos permitidos: `description`, `mode`, `untagged_vlan`, `tagged_vlans`. Status, enabled, IP, MAC e tipo não são alterados.
- Descrição ausente, null ou inválida é preservada. Texto vazio só limpa o destino quando `allow_description_clear=true`. Null sempre preserva.
- VLANs ficam desativadas no perfil inicial. Quando habilitadas, dados inconclusivos preservam as associações; uma descrição válida ainda pode ser atualizada.
- Erros de coleta/identidade impedem aplicar o lote. Inconclusões de campo preservam aquele campo e aparecem no resumo.
- O destino é relido antes e depois do PATCH. Timeout não provoca reenvio automático.
- Aplicação interrompe o lote após a primeira falha. Alterações já confirmadas permanecem; não existe transação entre interfaces nem rollback automático.

## Produção e agendamento

```bash
.venv/bin/python -m wug sync --all-devices --dry-run
.venv/bin/python -m wug sync --all-devices --apply
```

`--non-interactive` só funciona junto a `--apply`; deve ser reservado a uma operação já homologada. Nenhum cron é instalado nesta entrega. O comando é de execução única, protegido por lock. O grupo WUG no perfil define a população consultada; grupo 0 pode abranger todo o inventário visível à conta.

## Evidências e códigos de saída

`logs/pilot.log` contém execução, propostas e avisos, com rotação e mascaramento de credenciais. `relatorios/<run_id>.json` contém hash do perfil, escopo, evidências de paginação, valores anteriores, payloads e resultado por interface. São dados corporativos locais ignorados pelo Git.

Estados de alteração: `planned`, `sending`, `confirmed`, `blocked`, `unconfirmed`. Um processo interrompido em `sending` exige conferir o NetBox antes de decidir o próximo passo. O relatório é evidência de alterações, não um backup completo do NetBox.

- 0: execução concluída sem erros/inconclusões detectadas.
- 1: comparação/aplicação com pendências, falha por objeto ou cancelamento pelo operador.
- 2: configuração, limite, coleta global, política, arquivo ou bloqueio de execução inválido.

Uma simulação com diferenças válidas pode retornar 0. Um GET bem-sucedido não comprova permissão de PATCH nem fidelidade ao equipamento físico.

## Testar sem APIs

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate.py
```

A suíte proíbe transporte real. Fixtures são sintéticas, não respostas homologadas do WhatsUp Gold. Consulte [validação](docs/VALIDACAO.md).

## Documentação

- [Instalação e operação](COMO_INSTALAR_E_TESTAR.md)
- [Contrato técnico](SINCRONIZACAO_WUG_NETBOX.md)
- [Contrato da API WUG](docs/CONTRATO_API_WUG.md)
- [Requisitos e permissões](REQUISITOS_WUG_NETBOX.md)
- [Segurança](docs/SEGURANCA.md)
- [Migração do IMC](docs/MIGRACAO_IMC.md)
- [Plano de implantação](docs/INICIO_DO_PROJETO.md)
- [Arquitetura futura](docs/ARQUITETURA.md)
- [Mapa de arquivos](LISTA_DE_ARQUIVOS.md)

Entradas antigas IMC encerram com mensagem de migração. O arquivo `.disabled` continua apenas como referência histórica, nunca importado. Markdown é a fonte dos PDFs; gere novamente com `python scripts/render_pdfs.py` após instalar `requirements-docs.txt`.
