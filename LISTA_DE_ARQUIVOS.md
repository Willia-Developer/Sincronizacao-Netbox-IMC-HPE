# Arquivos do projeto WhatsUp Gold -> NetBox

## Código operacional

- wug/__main__.py: CLI e coordenação, sem rede no import.
- wug/client.py: autenticação e coleta WUG somente leitura.
- wug/profile.py: validação do contrato e gate de homologação.
- wug/models.py: Device, Interface, VlanState e ausência explícita.
- wug/policy.py: métodos, recursos, destino e campos permitidos.
- wug/netbox_client.py: consultas e PATCH individual de interface existente.
- wug/sync.py: planejamento, comparação independente por campo e aplicação.
- wug/runtime.py: configuração, logs, lock e relatório atômico.

## Configuração e dependências

.env.example e config/wug.example.json são modelos sem credenciais reais. .env e config/wug.json são locais e ignorados pelo Git. requirements.txt atende execução; requirements-dev.txt adiciona testes; requirements-docs.txt atende geração PDF.

## Testes e ferramentas

tests/conftest.py bloqueia rede real. tests/test_integration.py verifica política, autenticação, paginação, campos, comparação, escrita, CLI e entradas antigas. scripts/validate.py agrega verificações. scripts/mock_dry_run.py executa um cenário sintético. scripts/review_repository.py confere links/perfil. scripts/render_pdfs.py gera PDFs. scripts/audit_security.py é auditoria histórica, sem alteração de histórico nem impressão de valores secretos.

scripts/executar_sincronizacao.sh executa a CLI usando SYNC_PYTHON_BIN. Não instala agendamento.

## Documentação

README.md, COMO_INSTALAR_E_TESTAR.md, SINCRONIZACAO_WUG_NETBOX.md, REQUISITOS_WUG_NETBOX.md e docs/ contêm operação, contrato, segurança, arquitetura futura e validação. PDFs da raiz são derivados atuais; nomes antigos com IMC permanecem somente por compatibilidade de arquivo.

## Legado e evidências

imc/*.py, imc/*.sh e sincronizacao_imc_netbox.py estão desativados. imc/legacy/netbox_client.py.disabled é referência inerte. whatsup_gold_imc/ aponta para os documentos atuais e não possui comparador operacional.

logs/, relatorios/ e artifacts/ são locais e ignorados. Não contêm dados reais nesta entrega versionada. Para inventário exato dos arquivos, use git ls-files.
