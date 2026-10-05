# Aceite operacional por etapa

Resultados offline estão em VALIDACAO.md. Esta lista contém validações ainda necessárias no ambiente real.

- Conexão WUG: versão/build, certificado, token e GET product.
- Inventário: grupo correto, total esperado, páginas, IDs e nomes; conta enxerga todo o escopo autorizado.
- Portas: validar que são portas físicas/stack, não interfaces IP de polling.
- Descrição: conferir campo administrativo e tratamento de null/vazio.
- VLAN: ativar somente com tagged/untagged/modo inequívocos. Conferir VLANs existentes e grupo NetBox.
- Simulação: evidência de antes/proposto sem PATCH em nenhum produto.
- Aplicação: PATCH apenas NetBox, conferência posterior, segundo dry-run idempotente.
- Falhas: credenciais inválidas, dados parciais, concorrência e timeout preservam controles.
- Recuperação: localizar relatório sending/unconfirmed e reconciliar estado, sem reaplicação cega.
- Operação: documentar responsável, frequência desejada, retenção e atendimento a códigos 1/2.

A aprovação de uma etapa não pode ser inferida de um teste mockado. Não há ambiente real acessado nesta entrega.
