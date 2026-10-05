# Contrato técnico da sincronização

## Direção e escopo

WhatsUp Gold -> coletor de leitura -> normalização -> comparação -> PATCH de interface NetBox. NetBox é consultado para calcular diferenças e confirmar escrita; nunca é origem de alterações destinadas ao WhatsUp Gold.

O escopo atual permanece descrição e VLANs de interfaces existentes. Não cria devices, interfaces ou VLANs; não exclui objetos; não altera habilitação, status, endereços, MAC ou tipo.

## Fonte e normalização

`wug/client.py` entrega Device e Interface definidos em models.py. Campos são mapeados pelo perfil da API instalada. Não existe fallback silencioso entre comentário de monitor, ifDescr e descrição administrativa. O nome de exibição WUG só é usado como chave se o perfil e os mapeamentos foram revisados.

MISSING, null e valor inválido preservam descrição. String vazia preserva por padrão; limpeza requer flag explícita. Valores válidos perdem apenas espaços nas extremidades; caixa e espaços internos são preservados.

VLAN desativada ou inconclusiva não gera payload de VLAN. Quando habilitada, modo é mapeado explicitamente para access ou tagged. VID deve estar entre 1 e 4094. Access requer VLAN untagged e nenhuma tagged. Tagged permite untagged null explicitamente confirmado. VLAN ausente no retorno não equivale a null. Uma VLAN não pode aparecer em ambas as listas. Não há inferência de hybrid/tagged-all.

## Identidade

O dispositivo é buscado pelo nome exato no NetBox. A interface é buscada pelo nome exato e device_id. Maps opcionais relacionam ID WUG de dispositivo ao nome NetBox e chave device_id:interface_id ao nome NetBox. IDs de produtos diferentes não são equivalentes. Duplicidades após mapeamento bloqueiam aplicação. Não há fallback por IP, posição ou abreviação.

## Planejamento

Todas as páginas de dispositivos são materializadas antes da comparação. Cada coleção de interfaces é completada antes de gerar propostas daquele dispositivo. Paginação inválida, IDs duplicados, inventário vazio ou nenhum par são reportados como erro. Device ausente é descartado sem criação; se nenhum par existe, o resultado geral é inconclusivo.

Descrição e VLAN são comparadas independentemente. Falha de identidade/coleta bloqueia aplicação do lote; problema restrito a um campo preserva aquele campo. A contagem de inconclusivos é por interface com pendência, não por campo.

## Aplicação

Campos autorizados: description, mode, untagged_vlan e tagged_vlans. Recurso permitido: PATCH individual em dcim/interfaces/{id}/. Primeiro persiste plano JSON; depois pede confirmação (ou usa --non-interactive explícito). O plano é recalculado em cada execução e não importado de arquivo.

Antes do PATCH, relê a interface e compara snapshot completo dos campos gerenciados. Mudança concorrente bloqueia e interrompe o lote. Isso reduz conflitos, mas GET/PATCH não forma transação atômica. Depois do envio, relê o destino e confirma os valores. Timeout é conciliado por GET sem reenviar o PATCH.

Na primeira falha de aplicação o lote para. Alterações anteriores podem ter sido confirmadas; não há atomicidade global nem rollback automático.

## Evidência e recuperação

Cada relatório guarda escopo, início/fim de atualização, hash do perfil, paginação, antes/proposto e status. Intenção sending é salva antes da rede. Se o processo for interrompido, confira manualmente cada item não confirmado. Relatório não é backup do banco.

Para reversão, valide o estado atual e use os valores anteriores como evidência para uma mudança controlada no NetBox. Não reaplique cegamente o snapshot: pode existir uma edição legítima posterior. Não há comando automático de rollback nesta versão.
