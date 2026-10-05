# Mapa da migração

Código operacional: wug/client.py, profile.py, models.py, policy.py, netbox_client.py, sync.py, runtime.py e __main__.py. Configuração: .env.example e config/wug.example.json. Wrapper: scripts/executar_sincronizacao.sh.

Testes: tests/test_integration.py e testes de CLI. Validação agregada: scripts/validate.py. Revisão documental: scripts/review_repository.py. PDFs: scripts/render_pdfs.py. Auditoria histórica: scripts/audit_security.py (ferramenta de investigação, não homologação).

As entradas IMC agora encerram com orientação. O legado .disabled continua inativo. As documentações canônicas são README.md, SINCRONIZACAO_WUG_NETBOX.md, REQUISITOS_WUG_NETBOX.md e docs/CONTRATO_API_WUG.md; nomes antigos são mantidos como redirecionamento.

Use git diff --stat e git diff para revisar a lista exata desta mudança.
