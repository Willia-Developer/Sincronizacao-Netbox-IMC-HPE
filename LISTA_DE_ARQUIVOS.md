# Mapa de arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| sincronizacao_imc_netbox.py | Entrada pela raiz |
| imc/sincronizacao_imc_netbox.py | CLI e ciclo único |
| imc/imc_client.py | GET iMC e parsing conservador |
| imc/netbox_client.py | Correspondências exatas e PATCH de interface |
| imc/policy.py | Métodos, allowlist e transporte restrito |
| imc/sync.py | Comparação, planejamento e aplicação |
| imc/runtime.py | Configuração, logs, mascaramento e lock |
| imc/legacy/netbox_client.py.disabled | Código antigo inativo |
| imc/executar_sincronizacao.sh | Wrapper com flock |
| imc/instalar_cron.sh | Agendamento desativado no piloto |
| imc/desinstalar_cron.sh | Remoção manual do agendamento legado |
| imc/testar_conexao_imc.py | Teste manual GET sem credenciais fixas |
| imc/.env.example | Configuração fictícia |
| imc/teste-home | Aviso em substituição ao dump interno |
| tests/ | Testes com mocks |
| scripts/mock_dry_run.py | Demonstração offline |
| scripts/audit_security.py | Auditoria do histórico sem segredos na saída |
| scripts/render_pdfs.py | Geração local dos PDFs derivados dos Markdown |
| docs/ | Relatório, auditoria histórica e procedimento de segurança |

A documentação oficial está em README.md, SINCRONIZACAO_IMC_NETBOX.md e COMO_INSTALAR_E_TESTAR.md. Os PDFs da raiz são derivados; não há apresentação PPTX no repositório auditado.
