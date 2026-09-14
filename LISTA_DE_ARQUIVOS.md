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
| imc/listar_dispositivos_imc.py | Lista IDs e nomes do inventário IMC |
| imc/inspecionar_switch_imc.py | Consulta interfaces/VLANs de um switch escolhido |
| imc/testar_conexao_netbox.py | Testa leitura dos três objetos necessários no NetBox |
| imc/comparar_dispositivos.py | Compara inventários; registra ausentes sem erro |
| imc/simular_switch.py | Dry-run de um único switch obrigatório |
| imc/aplicar_switch.py | Aplicação do switch com confirmação interativa |
| imc/sincronizar_producao.py | Inventário completo, dry-run padrão e aplicação explícita |
| imc/etapas.py | Implementação compartilhada das etapas e argumentos |
| imc/.env.example | Configuração fictícia |
| imc/teste-home | Aviso em substituição ao dump interno |
| tests/ | Testes com mocks |
| scripts/mock_dry_run.py | Demonstração offline |
| scripts/validate.py | Verificações offline consolidadas e artifacts/validation.json |
| docs/INICIO_DO_PROJETO.md | Preparação atual e roteiro de execução futura |
| docs/VALIDACAO_ETAPAS.md | Evidências da entrega incorporada à pasta principal |
| scripts/audit_security.py | Auditoria do histórico sem segredos na saída |
| scripts/render_pdfs.py | Geração local dos PDFs derivados dos Markdown |
| docs/ | Relatório, auditoria histórica e procedimento de segurança |

A documentação oficial está em README.md, SINCRONIZACAO_IMC_NETBOX.md e COMO_INSTALAR_E_TESTAR.md. Os PDFs da raiz são derivados; não há apresentação PPTX no repositório auditado.
