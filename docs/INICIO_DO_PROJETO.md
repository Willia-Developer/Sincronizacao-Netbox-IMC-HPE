# Guia de início do projeto

## Situação atual

Preparação local, sem APIs iMC ou NetBox disponíveis. O código por etapas e a documentação foram incorporados à pasta principal. Não é necessário recuperar arquivos de /tmp nem retomar a sessão anterior para usar esta entrega.

O iMC será a fonte da verdade. A integração somente poderá alterar descrição e VLANs de interfaces já existentes no NetBox. Não cria inventário nem altera os switches. Laboratório: um switch selecionado. Produção futura: todos os dispositivos do iMC, descartando e registrando os ausentes no NetBox.

## Agora: validar sem serviços

Na raiz do projeto, com Python 3.10 ou superior:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/mock_dry_run.py
.venv/bin/python scripts/validate.py
```

A instalação dos pacotes requer acesso ao repositório de dependências ou um espelho local, mas não às APIs do projeto. O verificador completo usa Git, Bash e pdftotext (pacote Ubuntu/Debian poppler-utils). A suíte bloqueia o transporte HTTP real. Não execute os scripts de conexão nesta fase: eles foram preparados para consultar serviços reais quando configurados.

Resultados: artifacts/validation.json, artifacts/pytest.txt e artifacts/mock_dry_run.txt. Código de saída zero do verificador indica sucesso em todas as verificações. Esses artefatos são locais e ignorados pelo Git.

## Depois: preparar o laboratório

Quando o projeto começar, providencie os endereços dos serviços, contas de acesso e certificados. Preencha imc/.env a partir de imc/.env.example, preservando um arquivo local já existente. Não versione esse arquivo nem execute source imc/.env.

Dispositivos, interfaces e VLANs devem existir previamente no NetBox. Os nomes precisam coincidir exatamente com os do iMC. Escolha explicitamente o grupo de VLAN quando houver VIDs repetidos em grupos diferentes. Exemplos não são configurações reais prontas para uso.

## Sequência futura

Execute uma etapa de cada vez na raiz, com a .venv ativa. Substitua SW-LAB-01 pelo nome exato encontrado na etapa 2.

| Etapa | Comando | Critério para avançar |
| --- | --- | --- |
| 1. Conexão iMC | `python imc/testar_conexao_imc.py` | GET autenticado bem-sucedido |
| 2. Descoberta | `python imc/listar_dispositivos_imc.py` | Identificar o nome exato do switch |
| 3. Inspeção | `python imc/inspecionar_switch_imc.py --device SW-LAB-01` | Conferir interfaces, descrições, PVID e VLANs |
| 4. Conexão NetBox | `python imc/testar_conexao_netbox.py` | Leitura de dispositivos, interfaces e VLANs |
| 5. Inventários | `python imc/comparar_dispositivos.py` | Conferir correspondências e descartes |
| 6. Simulação | `python imc/simular_switch.py --device SW-LAB-01` | Revisar propostas; zero escrita |
| 7. Aplicação controlada | `python imc/aplicar_switch.py --device SW-LAB-01` | Confirmar SIM e conferir resultados por GET |
| 8. Repetição | Repetir o comando da etapa 6 | Nenhuma proposta nova se a origem não mudou |

Uma falha ou VLAN inconclusiva deve ser resolvida antes da aplicação daquela interface. Hybrid sem classificação inequívoca é bloqueado. A interpretação de trunk/PVID deve ser conferida com o iMC instalado durante a inspeção. Mocks não certificam a semântica de uma versão real do iMC.

## Produção futura

Após validar o laboratório, use `python imc/sincronizar_producao.py --dry-run` para planejar todo o inventário. A escrita exige --apply; execução sem confirmação também exige --non-interactive explicitamente.

Dispositivo ausente no NetBox é um descarte esperado, registrado pelo nome. Interfaces e VLANs ausentes ou ambíguas são pendências; nenhum objeto é criado para corrigir essas ausências.

O instalador de cron continua desativado e nenhum agendamento foi criado. Todas as entradas executam uma vez. Implantação, agendamento e publicação não foram realizados nesta preparação.

## Referências

- [README operacional](../README.md): configuração, comandos, logs e contadores.
- [Validação desta entrega](VALIDACAO_ETAPAS.md): evidências locais e limites.
- [Contrato técnico](../SINCRONIZACAO_IMC_NETBOX.md): campos e endpoints implementados.
- [Segurança](SEGURANCA.md): registro histórico e configuração local.

Relatórios de auditoria antigos são históricos. A entrega offline não certifica rotação de credenciais, estado de servidores ou limpeza de um remoto Git.
