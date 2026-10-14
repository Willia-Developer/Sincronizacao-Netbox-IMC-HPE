# Contrato proposto da comparação WhatsUp Gold ↔ iMC

Status: especificação para implementação posterior. As regras deste documento não estão implementadas por um comparador.

## 1. Perguntas que o relatório deve responder

1. Quais dispositivos do escopo aparecem em cada sistema?
2. Quais registros representam, com evidência suficiente, o mesmo equipamento?
3. Para cada par confirmado, quais campos são iguais, diferentes ou não verificáveis?
4. Há duplicidades, coleta parcial, informação antiga ou significado incompatível?
5. Que ação de investigação a equipe precisa realizar para cada pendência?

Nenhuma fonte ganha precedência automática. iMC ser fonte da sincronização NetBox não o torna autoridade incontestável nesta auditoria.

## 2. Fluxo e isolamento

```text
WhatsUp Gold → adaptador de leitura → snapshot normalizado WUG ┐
                                                             ├→ associação → comparação → relatório
iMC         → adaptador de leitura → snapshot normalizado iMC ┘
```

Os adaptadores preservam valor original e proveniência. O comparador é offline, recebe snapshots e não tem clientes HTTP. O relatório não contém payloads de correção. A camada de coleta não importa a integração iMC–NetBox.

## 3. Registro de coleta e modelo comum

Cada snapshot deve conter `schema_version`, `run_id`, origem, versão/build do produto, início/fim UTC, escopo e filtros efetivos, páginas lidas, contagem de registros, estado de completude e erros. Guardar hash SHA-256 do arquivo de evidência local e referência ao mapeamento/configuração usado. Hash comprova integridade do artefato, não veracidade da fonte.

Cada dispositivo terá ID nativo, contexto administrativo/localidade, classe do objeto (equipamento físico, stack ou equipamento virtual), campos e metadados de qualidade. IDs nativos de dois sistemas diferentes não são chaves de igualdade. Serial do chassis, serial de um membro e serial lógico não são intercambiáveis.

Cada campo terá valor original, valor normalizado, estado de coleta, origem semântica (por exemplo, nome exibido ou SNMP sysName), horário de observação na fonte quando disponível e horário de extração. Campo não retornado, `null`, vazio conhecido, indisponível e erro precisam ser distintos. Arrays vazios só provam ausência quando a coleta daquela coleção foi completa.

## 4. Matriz de campos

| Campo comum | Comparação proposta | Cuidados |
| --- | --- | --- |
| Nome técnico / sysName | Texto com normalização explicitamente configurada | Nome de exibição pode ser apelido manual; não substituir sysName silenciosamente |
| IP de gerenciamento | IP canônico, com IPv4/IPv6 e contexto de rede | Não confundir IP primário de monitoramento com qualquer IP de interface, VIP ou NAT |
| Fabricante/modelo | Texto; equivalências somente por tabela revisada | sysDescr é texto livre, não modelo estruturado garantido |
| Serial | Exato por entidade física e fabricante | Sem inferir a partir de ID interno; stacks podem ter vários seriais |
| Localização | Texto ou catálogo de equivalências acordado | Grupo WUG, sysLocation e site iMC podem significar coisas diferentes |
| Estado operacional | Mapeamento explícito e horário de observação | Down, maintenance, unknown e falha de coleta são diferentes |
| Interfaces | Conjuntos e atributos dentro do dispositivo confirmado | ifIndex pode mudar; abreviação/ifAlias não são identidade universal |
| VLANs | VID, contexto, porta, modo e associação tagged/untagged | Não usar IDs internos entre produtos; lista de VLANs do device não prova VLAN de cada porta |

Primeira etapa proposta: presença, nome técnico e IP de gerenciamento. Fabricante, modelo e serial são candidatos condicionados ao levantamento. Interfaces, VLANs e estado operacional ficam desativados inicialmente. Não presumir que WhatsUp Gold exponha todos esses campos na API instalada.

## 5. Associação dos registros

Antes de procurar pares, detectar IDs duplicados, chaves repetidas e conflitos dentro de cada snapshot. Não aceitar correspondência muitos-para-um. Um registro pareado deixa de estar disponível para outro par, e toda decisão guarda a regra e os valores que a sustentam.

Ordem proposta:

1. Mapeamento explícito entre IDs nativos, revisado pela equipe. Conflito com identidade física continua visível e exige revisão; a tabela não pode ocultá-lo.
2. Serial + fabricante + classe/contexto compatíveis, únicos nos dois lados. Validar especificamente stacks e equipamentos virtuais antes de usar serial.
3. Nome técnico normalizado + IP de gerenciamento + contexto, todos presentes e únicos, sem conflito de serial conhecido. Registrar que a associação usou nome/IP; essa evidência é mais fraca que identidade física confirmada.
4. Nome isolado ou IP isolado geram candidato para análise, nunca pareamento definitivo automático. Conflitos, múltiplos candidatos e identidade insuficiente são inconclusivos.

Nome e IP divergentes ainda podem ser comparados quando um serial confiável ou mapeamento revisado confirma a identidade. Não transformar candidatos ambíguos em “só em um sistema”: primeiro separar os registros ainda não resolvidos.

Normalizações não poderão remover domínio DNS, ignorar caixa, expandir nome de porta ou mapear fabricante automaticamente. Habilitar somente as regras acordadas, preservando valores originais e detectando colisões após normalização. Não remover zeros ou caracteres de serial por suposição.

## 6. Escopo, completude e atualização

Definir a mesma população nos dois produtos. Inventário iMC de switches e inventário WUG com servidores/impressoras não têm escopos automaticamente equivalentes. Cada filtro precisa de contagens de incluídos, excluídos e motivo, por origem. Uma consulta pode ser completa para a conta e ainda assim não cobrir a população pretendida; verificar permissões por amostra conhecida.

Só declarar “somente no WUG” se a coleta iMC correspondente estiver completa e o pareamento estiver resolvido. A regra inversa também vale. Falha de autenticação, página perdida, timeout, limite excedido ou visibilidade desconhecida bloqueiam conclusões de ausência.

Inventários vazios, zero pares ou escopo ainda indefinido resultam em inconclusivo. Uma resposta HTTP 200 não basta. Registrar filtros, paginação, erros, contagens e evidência de término da coleta conforme a API real. Paginação por offset em inventário mutável não cria um snapshot atômico; registrar a janela e divergências entre contagens, realizando nova coleta quando necessário.

Idade máxima por campo e diferença máxima entre observações serão definidas com os intervalos reais de polling. O horário da extração não substitui a última observação na fonte. Na ausência desta, o resultado pode descrever igualdade dos valores armazenados, mas não atestar informação atual. Se atualização é requisito do campo e falta evidência, o campo é inconclusivo.

## 7. Estados e relatório

Separar três dimensões, para uma diferença conhecida não apagar uma falha de coleta:

| Dimensão | Estados previstos |
| --- | --- |
| Associação | `pareado`, `somente_wug`, `somente_imc`, `ambiguo`, `nao_resolvido` |
| Comparação por campo | `igual`, `divergente`, `inconclusivo`, `fora_do_escopo` |
| Qualidade | `completo`, `parcial`, `desatualizado`, `sem_horario`, `erro_coleta` |

O relatório deverá ter resumo de cobertura e detalhes por dispositivo/campo: IDs de ambas as fontes, valores, horários, regra de associação, transformação aplicada, conclusão, motivo e referência de evidência. Dados ausentes em ambos os lados são inconclusivos, não iguais.

Denominadores precisam ficar explícitos: total em cada fonte, excluídos, pares, exclusivos, ambíguos, campos esperados, comparados, divergentes e inconclusivos. Uma taxa de concordância, se usada, deve vir acompanhada da cobertura; 100% dos dois campos disponíveis não significa 100% do inventário.

Formatos iniciais previstos: JSON estruturado e resumo Markdown. Inventário real fica em `relatorios/`, ignorado pelo Git. Qualquer futura exportação CSV deverá tratar fórmula de planilha em campos de texto livre.

Proposta de códigos de saída do futuro comparador: `0` para escopo não vazio, coleta válida, identidade resolvida e todos os campos obrigatórios verificáveis e iguais; `1` para divergências ou exclusivos com evidência completa; `2` para erro, ambiguidade, falta de cobertura/atualização exigida ou parametrização inválida. Se houver divergências e incerteza juntas, retornar `2` e conservar ambas no relatório.

Concordância final é sempre limitada ao escopo, aos campos selecionados e à janela observada. Para afirmar aderência ao equipamento físico, usar validação externa por amostragem, com data e responsável.
