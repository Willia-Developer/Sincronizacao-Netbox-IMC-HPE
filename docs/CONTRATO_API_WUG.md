# Perfil da API WhatsUp Gold instalada

## O que está confirmado e o que depende do ambiente

A documentação pública oficial descreve POST /api/v1/token para autenticação, GET product e GET device-groups/{id}/devices, com data.devices e paginação por nextPageId. Essas referências são antigas e não homologam a versão da empresa.

Fontes consultadas em 05/10/2026:
- https://docs.ipswitch.com/api/
- https://www.whatsupgold.com/rest-api

O Swagger da instalação é a referência para versão, caminhos e respostas. O coletor NÃO presume que DeviceTemplateInterface represente porta física: na documentação pública esse objeto inclui endereço/nome de rede para polling. Não usar esse objeto para preencher VLAN de switch sem evidência.

## Criar o perfil

Copie config/wug.example.json para config/wug.json. Credenciais pertencem ao .env, nunca ao perfil. Configuração real é ignorada pelo Git.

- schema_version: 1.
- validated: false até homologação.
- product_version: versão/build da instalação.
- validated_by, validated_at, evidence: responsável, data e referência local/chamado que registra amostras e testes. Não guardar segredos.
- allow_description_clear: false por padrão. True permite limpar apenas string vazia; null continua preservando.
- device_map: objeto ID WUG -> nome exato NetBox.
- interface_map: objeto "ID_DEVICE:ID_INTERFACE" -> nome exato da interface NetBox.

## Coleções

Cada coleção define endpoint relativo a /api/v1/, items_path, id_field e name_field. Caminhos de campos usam pontos para percorrer objetos JSON; o coletor não executa expressões nem usa alternativas automáticas.

Dispositivos: endpoint device-groups/N/devices. Restrinja o grupo conforme o piloto. O nome default é name (nome de exibição), não sysName garantido. Use mapeamento explícito se não representar o cadastro técnico.

Portas físicas: endpoint inicialmente null. Formatos aceitos pelo cliente são devices/{device_id}/interfaces, devices/{device_id}/inventory/interfaces ou devices/{device_id}/reports/<nome>. Esses formatos delimitam a política, NÃO atestam que o recurso exista. Se a instalação expõe outro contrato, adapte o cliente e seus testes; não remova as restrições de destino.

description_field deve apontar para a descrição administrativa confirmada. Não mapear genericamente comments ou nome de interface para descrição. IDs da coleção devem ser números inteiros não negativos ou strings decimais; outro formato exige adaptação explícita.

## Paginação e completude

- cursor: container_path (por exemplo paging), next_field (nextPageId), parameter (pageId). O container precisa existir em todas as respostas; próximo cursor ausente/null/vazio encerra a coleção conforme esse contrato. Uma lista curta não encerra por si só.
- offset: total_path, parameter e limit_parameter. Total deve ser inteiro estável; offset avança pelo número real de itens recebidos, inclusive em páginas menores que o limite pedido.
- none: complete_path precisa apontar para booleano true. Não habilite esse modo se a resposta não comprovar a coleção completa.

Limites do cliente: 1000 páginas e 100000 registros por coleção; exceder qualquer limite rejeita a coleta. IDs/cursor repetidos e páginas vazias com continuação são erros. Não há snapshot transacional da fonte; a janela de extração e contagens não garantem ausência de mudanças no meio da coleta.

## VLAN

vlans.enabled começa false. Para habilitar: defina mode_field, untagged_field, tagged_field e mode_map. Os valores de destino de mode_map devem ser access ou tagged. tagged_field deve retornar lista de VIDs, não IDs internos de outro sistema. Sem tagged/untagged confirmado, preserve o NetBox.

Exemplo somente de representação NORMALIZADA, não uma resposta real WUG: modo tagged, untagged 10, tagged [20, 30]. O conector resolve esses VIDs para IDs do NetBox no grupo configurado.

## Homologação necessária

Conferir em um switch: identidade física/stack, nomes das portas, descrição administrativa, porta access, trunk, VLAN nativa e tagged, campo ausente/null e retorno paginado. Comparar com configuração real e registrar data da observação. Não usar horário da extração como prova da atualização do dado na fonte.

A aplicação exige validated=true e metadados preenchidos. Esse gate registra a decisão local; não verifica automaticamente um chamado, assinatura ou verdade física. Se a API não fornece VLANs confiáveis, mantenha-as desativadas e homologue somente descrição.
