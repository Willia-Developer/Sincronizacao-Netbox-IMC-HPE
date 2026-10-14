# Revisão do projeto iMC–NetBox e implicações para a próxima fase

Data: 22/09/2026. Base: `065e8870f53b0e0135a4288a55d531e28b2b4f70`. A árvore estava limpa ao iniciar a revisão. Escopo: implementação ativa, entradas CLI, scripts auxiliares, testes, configuração de exemplo, documentação e isolamento do legado. Nenhuma API corporativa foi acessada.

## Resultado

O projeto atual implementa uma sincronização limitada de descrição e VLANs de interfaces existentes no NetBox. Suas regras e testes oferecem uma base de referência, mas **não entregam auditoria de equivalência completa de dispositivos**, nem integração com WhatsUp Gold.

O código operacional existente foi preservado. Os pontos abaixo são resultados da revisão e requisitos para uma evolução separada; não representam correções já implementadas.

## Mapa da implementação revisada

| Área | Arquivos | Constatação |
| --- | --- | --- |
| Entrada | `sincronizacao_imc_netbox.py`, `imc/sincronizacao_imc_netbox.py` | Encaminhamento para a CLI; dry-run padrão; aplicação exige escopo |
| Etapas | `imc/etapas.py` e entradas de conexão/listagem/inspeção/comparação/simulação/aplicação/produção | Serviços podem ser testados isoladamente; laboratório seleciona um switch |
| iMC | `imc/imc_client.py` | Digest, GET, parsing XML/JSON, paginação e classificação de VLAN |
| NetBox | `imc/netbox_client.py` | Busca exata; grupo VLAN opcional; GET e PATCH individual restrito |
| Regras | `imc/policy.py`, `imc/sync.py` | Allowlist, plano de mudanças, confirmação, releitura e verificação posterior |
| Execução | `imc/runtime.py`, `imc/executar_sincronizacao.sh` | Configuração como dados, TLS, mascaramento, rotação de logs e locks locais |
| Agendamento | `imc/instalar_cron.sh`, `imc/desinstalar_cron.sh` | Instalação desativada; remoção de cron é ação manual e não foi executada |
| Legado | `imc/legacy/netbox_client.py.disabled`, `imc/teste-home` | Legado bloqueado; antigo dump substituído por aviso |
| Testes | `tests/conftest.py`, `tests/test_pilot_policy.py`, `tests/test_imc_netbox_core.py`, `tests/test_etapas.py` | Transporte HTTP real bloqueado; mocks cobrem limites e fluxos principais |
| Ferramentas | `scripts/validate.py`, `mock_dry_run.py`, `review_repository.py`, `audit_security.py`, `render_pdfs.py` | Verificação offline, revisão estática, auditoria local e documentos derivados |
| Documentação | README, contrato técnico, guias, requisitos, mapa e relatórios em `docs/` | Escopo de escrita documentado; relatórios antigos marcados como históricos |
| Configuração | `.gitignore`, `imc/.env.example`, `requirements.txt` | Segredos/artefatos locais ignorados; dependências por intervalo, sem lock de versões |

## Validação repetida nesta revisão

Comando executado na raiz: `.venv/bin/python scripts/validate.py`.

- 105 testes e 86 subtestes passaram.
- Compilação Python, sintaxe de cada Bash, dependências, revisão estática, links locais e extração textual dos cinco PDFs passaram.
- Simulação mockada: uma proposta e zero PATCHes.
- `git diff --check` passou na base revisada.

As saídas completas estão em `artifacts/validation.json`, `artifacts/pytest.txt` e demais arquivos locais de `artifacts/`. A revisão de PDFs feita pelo verificador é textual; não certifica diagramação visual. A suíte não certifica endpoints, dados, permissões ou versões reais dos produtos.

## Achados que afetam a ideia de “mesmas informações”

| Prioridade para a auditoria | Evidência na base | Consequência | Decisão para a nova fase |
| --- | --- | --- | --- |
| Alta | `imc/etapas.py:72`, `imc/sync.py:138`: percorrem o iMC e buscam nomes no NetBox | Não enumeram o inventário exclusivo do destino; igualdade nos dois sentidos não é demonstrada | Coletar ambos os inventários por completo e comparar sua união |
| Alta | `imc/etapas.py:72` e `imc/netbox_client.py:81`: correspondência por nome | Nome igual não verifica IP, modelo ou serial | Identidade com evidências e comparação por campo |
| Alta | `imc/etapas.py:72`, `imc/sync.py:138`: lista vazia não gera erro | Execução bem-sucedida pode ter comparado zero dispositivos | Declarar escopo vazio/incompleto como inconclusivo |
| Alta | `imc/sync.py:76` e `imc/sync.py:186`: descrição ausente é preservada e VLAN igual pode contar como sincronizada | Contador não garante que todos os campos foram verificados | Registrar cobertura e condição de cada campo; desconhecido não é igual |
| Alta | `imc/etapas.py:50`: inspeção de zero interfaces retorna sucesso | Ausência de interfaces pode passar despercebida ao avaliar cobertura | Exigir completude e expectativa compatível com o tipo de dispositivo |
| Alta | Não há timestamp de observação por atributo nem contrato de coleta completa | Respostas recentes podem conter inventário antigo; visibilidade parcial pode parecer ausência | Validar idade, janela entre fontes e permissões do escopo |
| Média | `imc/sync.py:149,173`: contagens repetidas; `imc/sync.py:70`: resolução VLAN por interface | Custo cresce com inventários/interfaces grandes; não houve benchmark de produção | Índices por identidade e cache apenas durante a coleta; medir antes de ampliar escopo |
| Média | `imc/imc_client.py:90`, `imc/netbox_client.py:56`: paginação sem orçamento total de execução | Timeout por requisição não limita o tempo total de uma coleta crescente | Limites de páginas, itens, tamanho, tentativas e duração; exceder limite torna coleta incompleta |
| Média | `imc/runtime.py:74`: lock por cópia do repositório | Dois clones/servidores não compartilham exclusão mútua | Execução independente e capacidade de API dimensionada; concorrência explicitamente controlada |
| Documentação | `docs/INICIO_DO_PROJETO.md` e `ALTERACOES_REALIZADAS.md` descrevem uma entrega anterior sem publicação | Esses trechos não são inventário do estado atual do GitHub | Tratar datas e etapas como evidência histórica; registrar nova execução com commit e horário |

As primeiras cinco observações foram conferidas no código; quatro delas também foram reproduzidas com dados sintéticos. Ausência de dispositivo no NetBox como descarte é comportamento intencional da sincronização existente. Não deve ser herdado como “inventários equivalentes” na auditoria futura.

## Experimentos adicionais, sem rede

Foram usadas as fixtures existentes com `requests.adapters.HTTPAdapter.send` bloqueado, sem carregar `.env`:

| Experimento | Resultado observado |
| --- | --- |
| Mesmo nome, IP iMC `192.0.2.10` e IP NetBox `192.0.2.20/24` | `compare_inventory` retorna `0`; não consulta interfaces nem compara esses IPs |
| Inventário iMC vazio | Zero propostas, zero erros e comparação retorna `0` |
| Interface sem `ifAlias`, mantendo VLAN igual | Zero propostas, `synchronized=1`, `errors=0` |
| Switch selecionado sem interfaces retornadas | `inspect_switch` retorna `0` |

Registro sintético local: `artifacts/revisao-projeto-2026-09-22.json`, na raiz do repositório. Esses experimentos expõem limites sem afirmar falha de um servidor real. Não foram acrescentados ao conjunto permanente de testes nem alteraram as regras existentes.

## Regras atuais que devem continuar protegidas

Aplicação explícita, somente quatro campos de interface, correspondências ambíguas bloqueadas, dry-run sem PATCH, TLS verificado, nova leitura antes/depois da alteração e reconciliação de comunicação incerta sem reenvio automático. Hybrid permanece inconclusivo; o significado real de PVID/tagged no iMC ainda exige validação de laboratório.

A futura auditoria não terá caminho de aplicação. A política HTTP do iMC atual também não deve ser copiada cegamente para o WhatsUp Gold: autenticação e contrato diferem, conforme [parametrização](PARAMETRIZACAO.md).

## Pendências reais e conclusão da análise

Confirmar no laboratório versões, respostas, paginação, escopo visível, semântica das VLANs e idempotência após aplicação autorizada. A rotação mencionada em [SEGURANCA.md](../docs/SEGURANCA.md) continua dependente do sistema de origem; esta revisão não atesta rotação ou limpeza de caches do GitHub.

A próxima fase deve começar como auditoria independente de leitura, com evidências e cobertura explícitas. A igualdade global só poderá ser declarada dentro do escopo e dos campos efetivamente verificados.
