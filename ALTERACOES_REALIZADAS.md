# Correções do piloto

O fluxo ativo foi reduzido à descrição e VLAN de interfaces existentes, com GET no iMC e GET/PATCH no NetBox, allowlist central, dry-run padrão e aplicação explícita.

Foram removidos do fluxo status, enabled, tipo físico, IP, MAC, metadados de dispositivos e criação de objetos. Referência histórica de criação permanece inativa em imc/legacy/netbox_client.py.disabled.

Foram acrescentados configuração validada, TLS verificado, logs com rotação e mascaramento, controle de concorrência, testes com mocks e proteção contra dados incompletos/ambíguos.

Exemplos e documentação foram sanitizados, o dump interno foi substituído por aviso e os PDFs foram regenerados. A credencial comprometida exige rotação manual; a limpeza histórica é tratada separadamente, conforme o relatório.

Detalhes, resultados e pendências em [relatório](docs/RELATORIO_FINAL.md). Contrato completo em [documentação técnica](SINCRONIZACAO_IMC_NETBOX.md).
