# Correções do piloto

## Entrega atual: preparação offline por etapas

Incorporada à pasta principal a implementação preparada na sessão anterior. O projeto não depende da cópia temporária. Não há APIs iMC/NetBox disponíveis nesta fase; a entrega foi validada com respostas simuladas.

- Scripts separados para conexão, descoberta, inspeção, comparação, simulação, aplicação de um switch e produção futura.
- Laboratório limitado ao switch escolhido; produção consulta todos e registra dispositivos ausentes no NetBox como descartes esperados.
- Grupo de VLAN opcional e confirmação por GET após PATCH, incluindo reconciliação de timeout sem reenvio automático.
- 105 testes e 86 subtestes aprovados; documentação operacional e cinco PDFs atualizados.
- Configuração local preservada; nenhum agendamento, acesso a APIs, commit ou push executado nesta entrega.

Veja o [guia de início](docs/INICIO_DO_PROJETO.md) e a [validação atual](docs/VALIDACAO_ETAPAS.md).

## Histórico da base do piloto

O fluxo ativo foi reduzido à descrição e VLAN de interfaces existentes, com GET no iMC e GET/PATCH no NetBox, allowlist central, dry-run padrão e aplicação explícita.

Foram removidos do fluxo status, enabled, tipo físico, IP, MAC, metadados de dispositivos e criação de objetos. Referência histórica de criação permanece inativa em imc/legacy/netbox_client.py.disabled.

Foram acrescentados configuração validada, TLS verificado, logs com rotação e mascaramento, controle de concorrência, testes com mocks e proteção contra dados incompletos/ambíguos.

Exemplos e documentação foram sanitizados, o dump interno foi substituído por aviso e os PDFs foram regenerados. A credencial comprometida exige rotação manual; a limpeza histórica é tratada separadamente, conforme o relatório.

Detalhes, resultados e pendências em [relatório](docs/RELATORIO_FINAL.md). Contrato completo em [documentação técnica](SINCRONIZACAO_IMC_NETBOX.md).
