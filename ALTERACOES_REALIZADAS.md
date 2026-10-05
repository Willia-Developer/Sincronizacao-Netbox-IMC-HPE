# Alterações realizadas - migração WhatsUp Gold

Nova origem: WhatsUp Gold. Destino único de escrita: NetBox. O IMC sai do fluxo operacional.

Foram adicionados cliente WUG com autenticação restrita, perfil de mapeamento, modelos neutros, comparação por campo, CLI, plano JSON e testes offline. Cliente NetBox e utilitários de runtime foram reaproveitados e adaptados.

Null/ausência preservam descrição; limpeza vazia exige configuração. VLAN inconclusiva não impede descrição confirmada. Ambiguidade/coleta inválida bloqueia aplicação. Limite de alterações e interrupção na primeira falha reduzem o alcance de uma execução problemática.

Entradas IMC foram desativadas com orientação de migração. Documentos foram reformulados e PDFs regenerados. Planejamento antigo WUG x IMC foi substituído por referências à arquitetura atual.

Não foram implementados dashboard, Sumos, SQL central, agendamento, rollback automático ou endpoints WUG presumidos para portas físicas. A API instalada ainda precisa ser homologada. Consulte docs/VALIDACAO.md para resultados efetivamente executados.
