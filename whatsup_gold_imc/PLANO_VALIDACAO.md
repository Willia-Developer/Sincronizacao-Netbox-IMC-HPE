# Plano de implementação e validação posterior

Status atual: análise e preparação. Não há estimativa de prazo vinculante antes de conhecer versões, escopo e respostas reais.

## Etapas e entregas

| Etapa | Trabalho | Critério para avançar |
| --- | --- | --- |
| 0. Encerrar o piloto iMC–NetBox | Validar no laboratório a integração existente, incluindo dry-run, aplicação autorizada e repetição | Evidência operacional separada; não apenas os 105 testes offline |
| 1. Levantar contratos | Versões, Swagger, acesso de leitura, escopo e amostras sanitizadas de ambos | Campos e paginação documentados; população equivalente definida |
| 2. Implementar coletas independentes | Adaptadores próprios dentro desta pasta; snapshots e metadados de completude | Nenhuma mutação de inventário; limites e falhas testados |
| 3. Implementar comparação offline | Identidade, normalização, diferenças e cobertura | Cenários sintéticos abaixo aprovados, sem clientes HTTP no comparador |
| 4. Executar piloto de auditoria | Coletar escopo pequeno e explícito, comparar e conferir na UI dos produtos | Todas as classificações conferidas por evidência; incertezas visíveis |
| 5. Conferir aderência à rede | Amostragem com equipe/equipamentos e mesma janela temporal | Fontes antigas ou incorretas identificadas sem eleger uma delas por suposição |
| 6. Ampliar escopo | Medir tempo/carga, limites, paginação e repetibilidade | Cobertura de toda a população acordada, sem saturar APIs |

Nenhuma destas etapas exige incorporar WhatsUp Gold ao código iMC–NetBox. A auditoria não incluirá aplicação automática, mesmo depois de homologada. Um eventual projeto de correção de dados terá decisão e escopo próprios.

## Cenários mínimos de teste do futuro comparador

| Caso | Resultado esperado |
| --- | --- |
| Inventários completos, pares únicos e todos os campos exigidos iguais | Igualdade no escopo; código `0` |
| Device presente só no WUG, com coleta iMC completa | `somente_wug`; código `1` |
| Device presente só no iMC, com coleta WUG completa | `somente_imc`; código `1` |
| Mesmo serial físico/contexto, nome ou IP diferente | Pareado por identidade, diferença de campo explícita |
| Mesmo nome, IP/serial conflitantes e sem identidade resolvida | Ambíguo; código `2`; não escolher primeiro resultado |
| Mesmo IP em localidades/VRFs distintas | Não associar por IP isolado |
| Nome curto/FQDN ou caixa diferente | Preservar diferença, salvo normalização explicitamente revisada |
| Normalização produz duas chaves iguais | Ambiguidade; nenhuma associação silenciosa |
| Stack com um cadastro lógico e vários membros físicos | Exigir modelo de identidade de stack; não associar a um membro arbitrário |
| Serial/modelo ausente em ambos | Campo inconclusivo; nunca igualdade por `null == null` |
| API omite campo ou retorna vazio, null, unknown | Estados distintos e motivo registrado |
| Inventário vazio ou zero pares | Inconclusivo; nunca 100% de concordância |
| Falha na segunda página, página repetida ou contagem inconsistente | Coleta incompleta; não concluir exclusivos |
| HTTP 401/403, timeout, 429 ou 5xx | Erro/recuperação limitada; falha final fica explícita |
| Limite de páginas, itens, resposta ou tempo atingido | Coleta parcial; código `2` |
| Conta não enxerga um grupo conhecido | Escopo não validado; não concluir ausência |
| Dados extraídos agora, mas observados há muito tempo | Desatualizado; não certificar estado atual |
| Sem horário de observação de campo que exige atualização | Inconclusivo; não usar horário de extração como substituto |
| Polling das fontes em janelas incompatíveis | Incerteza temporal registrada |
| Interfaces com nomes/ifIndex inconsistentes | Revisar identidade de porta antes de comparar VLAN/descrição |
| VLAN conhecida em uma fonte, sem API correspondente na outra | Capacidade insuficiente; não preencher por inferência |
| Token em erro/log e atributo com quebra de linha | Segredo mascarado; texto não pode forjar registro |
| Endpoint de escrita ou redirecionamento para outra origem | Bloqueado antes de enviar |
| Mesmo par de snapshots, mesma configuração | Mesmas conclusões e ordenação determinística |
| Diferença real junto de coleta parcial | Mostrar ambas; resultado global `2` |

Os testes HTTP deverão usar fixtures sanitizadas e bloquear rede real. Testes da auditoria ficam nesta pasta e têm comando próprio; não depender de importações do pacote `tests/` da integração atual. A regressão iMC–NetBox poderá ser executada separadamente para comprovar que o isolamento foi mantido.

## Evidência exigida para homologação real

Guardar localmente os snapshots, commit do coletor, configuração sem segredos, hashes, versões, início/fim, escopo, completude e relatório. Conferir uma amostra que inclua pares iguais, exclusivos, divergências, duplicidades e campos indisponíveis. Quando uma classe não existir no laboratório, mantê-la coberta por teste sintético e declarar esse limite.

A equipe deve conferir IP/nome/serial nas telas apropriadas e, quando a pergunta for sobre a configuração real, também nos equipamentos ou em evidência independente autorizada. Registrar último polling e distinguir dados manuais de dados descobertos.

Não precisa haver zero divergências para a ferramenta ser homologada: ela precisa classificar corretamente as divergências conhecidas e a falta de evidência. Um relatório com divergências é uma execução útil; uma conclusão de igualdade sem cobertura suficiente é falha de aceite.

## Pendências desta preparação

Versão WhatsUp Gold/iMC, escopo definitivo, campos prioritários, amostras/API e limites temporais ainda não definidos. Conectores, comparador, relatórios operacionais e testes da nova implementação serão entregues nas etapas futuras. Nenhum acesso real, alteração de inventário, agendamento ou implantação foi realizado nesta preparação.
