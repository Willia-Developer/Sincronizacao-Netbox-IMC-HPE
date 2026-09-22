# Parametrização e contratos das APIs — fase futura

O [exemplo JSON](config/parametros.example.json) registra decisões propostas, sem ativar execução. Valores `null` indicam pendências; não são configurações válidas para coleta real. Não há carregador/validador de configuração implementado nesta etapa.

## Levantamento necessário

| Tema | WhatsUp Gold | iMC |
| --- | --- | --- |
| Produto | Versão, build, módulos e licença efetivos | Versão, build e módulos efetivos |
| API | Swagger/OpenAPI da instalação e exemplos sanitizados | Contrato REST e exemplos XML/JSON da instalação |
| Conectividade | URL, porta, proxy, CA e rota autorizados | URL, porta, proxy, CA e rota autorizados |
| Autenticação | Fluxo efetivo de emissão/renovação e expiração | Método de autenticação confirmado; implementação atual usa Digest |
| Escopo | Grupos, subgrupos, dispositivos incluídos e visibilidade da conta | Dispositivos incluídos e visibilidade da conta |
| Inventário | Endpoint de enumeração, paginação e contagem | Endpoint de enumeração, paginação e contagem |
| Campos | Origem/semântica de nome, IP, modelo, serial e localização | Mesmos conceitos, sem presumir os mesmos nomes de campos |
| Atualização | Última observação por dado, polling e descoberta | Última observação por dado, polling e descoberta |

Amostras precisam incluir mais de uma página, dispositivo com informação ausente, duplicidade, estado desconhecido e stack caso exista no escopo. Sanitizar credenciais e informações corporativas antes de versionar qualquer fixture.

## O que foi verificado na documentação pública

A referência oficial histórica descreve emissão de token por `POST /api/v1/token`, uso de Bearer e leituras de dispositivos e atributos. Esses exemplos orientam o levantamento; não garantem endpoints, campos ou licenças da instalação a ser usada. [Referência REST oficial](https://docs.ipswitch.com/api/).

O fabricante disponibiliza interface Swagger para explorar o contrato REST. Ela deve ser usada para conferir as capacidades da versão instalada, com atenção para não executar ações de alteração durante o levantamento. [REST API do WhatsUp Gold](https://www.whatsupgold.com/rest-api).

O índice oficial encaminha versões 2023 e posteriores para a documentação Progress. A versão do ambiente ainda não foi informada; os caminhos HTTP não foram fixados no exemplo de configuração. [Índice oficial de documentação](https://docs.ipswitch.com/en/whatsup-gold.html).

As fontes foram consultadas em 22/09/2026. A existência de um endpoint de atributos não demonstra que modelo, serial ou VLAN por porta estejam preenchidos, atualizados ou disponíveis nessa instalação.

## Política de acesso proposta

- Coletar inventário apenas por operações de leitura confirmadas no contrato. Não solicitar redescoberta, polling forçado, manutenção, criação, exclusão ou correção de atributos.
- Se o fluxo instalado usar POST para token, permitir exclusivamente o endpoint de autenticação validado. Essa exceção não permite POST de inventário. Tokens permanecem em memória e fora de relatórios/logs.
- HTTPS com certificado verificado e CA interna quando necessário. Não copiar opções que desativem TLS de exemplos externos.
- URLs e métodos dos adaptadores terão allowlist, paginação limitada, redirecionamentos bloqueados e timeout. Não seguir links de próxima página para outra origem.
- Falha, limite ou token expirado sem recuperação segura deixa a coleta incompleta; não converter erro em lista vazia.
- Dados reais e logs terão acesso local restrito. A proteção do `.gitignore` evita adição acidental, mas não substitui permissões de arquivo nem revisão antes de publicar.

Estas são exigências de implementação futura, não controles já executados por um conector.

## Configuração independente

Configuração operacional futura: `config/parametros.local.json` e `.env` dentro de `whatsup_gold_imc/`, ambos ignorados. Nenhuma leitura implícita de `../imc/.env`. Nomes de variáveis propostos: `AUDIT_WUG_USERNAME`, `AUDIT_WUG_PASSWORD`, `AUDIT_IMC_USERNAME`, `AUDIT_IMC_PASSWORD`; valores devem permanecer locais.

O futuro carregador deverá rejeitar campos desconhecidos, placeholders e combinações incompletas. URLs/endpoints `null`, versão não validada, escopo não confirmado ou limites temporais indefinidos impedem execução operacional. Senhas nunca entram no JSON; usar referências a variáveis/segredos locais. Não criar mecanismos de execução de expressões, `eval`, shell ou imports configuráveis para mapear campos.

## Mapeamento semântico

Os caminhos de campos das APIs ficarão pendentes até haver respostas reais sanitizadas. O campo comum `technical_name`, por exemplo, não poderá receber um nome de exibição sem que essa equivalência seja validada. Diferenciar IP de monitoramento, IP de gerenciamento e lista de IPs de interfaces.

Cada mapeamento terá origem, caminho do campo, tipo, unidade, regra de normalização, capacidade comprovada e amostra que o valida. Fabricante/modelo/serial extraídos de texto livre exigem regra revisada e teste; ausência de correspondência não vira string vazia equivalente.

Limites de idade, diferença entre coletas, quantidade de páginas e duração são decisões operacionais. Os números de timeout e orçamento no exemplo são propostas conservadoras para um piloto, não limites certificados dos produtos. Escopo por IDs/grupos usa IDs próprios de cada fonte e precisa representar a mesma população; uma lista vazia não significa “todos”.
