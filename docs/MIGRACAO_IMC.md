# Migração do IMC para WhatsUp Gold

## Alterações incompatíveis

O pacote operacional agora é wug/. Use python -m wug. Entradas antigas em imc/ e sincronizacao_imc_netbox.py encerram sem rede e apontam para a documentação. Nenhuma credencial IMC é carregada pelo novo fluxo.

.env.example fica na raiz. IMC_ENV_FILE foi substituído por SYNC_ENV_FILE. WUG_URL inclui a origem HTTPS e porta real, sem /api. NETBOX_URL também deve ser uma origem HTTPS. HTTP não é aceito.

Mapeamento da API está em config/wug.json local. Não migrar credenciais por cópia automática. O endpoint de portas físicas deve ser confirmado no Swagger instalado; não existe equivalência presumida com VLAN endpoints do IMC.

## Comportamentos alterados

- Null de descrição agora preserva o destino.
- Limpeza por string vazia exige allow_description_clear=true.
- VLAN inconclusiva preserva VLAN e permite descrição válida.
- Plano com erro de coleta/identidade bloqueia aplicação do lote.
- Falha durante aplicação interrompe os itens seguintes.
- Relatório JSON registra intenção antes do PATCH e resultado posterior.
- Escopo explícito exigido também em simulação.
- Nenhum agendamento é instalado/removido automaticamente.

## Procedimento de troca

1. Identifique e suspenda manualmente agendamentos IMC existentes com o responsável pelo servidor.
2. Preserve evidências anteriores e confira a versão do código.
3. Instale dependências em venv, crie .env e perfil local novos.
4. Execute testes offline, conexão, inspeção e simulação.
5. Homologue os campos reais e aplique somente um switch.
6. Atualize procedimentos de operação e monitoramento da execução.

O arquivo imc/legacy/netbox_client.py.disabled permanece como referência inativa; não restaurar/importar. Histórico Git permanece intacto. Os documentos antigos agora direcionam ao contrato vigente.
