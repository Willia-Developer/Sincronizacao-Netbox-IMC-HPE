# Segurança e limites operacionais

## Fronteiras de escrita

WUG: GET somente nas rotas de leitura definidas; POST somente token com grant_type=password, username e password. Demais métodos/recursos bloqueados no request e no envio de PreparedRequest. Não há logout remoto, rediscovery, poll, manutenção ou escrita de configuração.

NetBox: GET em devices/interfaces/VLANs e PATCH individual de interface somente em modo apply. Campos autorizados: description, mode, untagged_vlan, tagged_vlans. Nada de criação, remoção ou PATCH em lote/dispositivo.

## Transporte e credenciais

HTTPS obrigatório, validação TLS ativa e CA interna opcional. Redirecionamentos desabilitados. Destino exato e caminhos canônicos verificados. Proxies e .netrc herdados não são utilizados; proxy pode ser configurado explicitamente sem credenciais na URL.

.env é lido como dados. Logs usam mascaramento de credenciais e quebras de linha; respostas brutas de erro/token não são registradas. Um token obtido fica somente em memória e é removido no encerramento. Expiração interrompe o processo; não existe refresh automático.

## Evidências locais

umask 077 na CLI, logs em diretório restrito, relatórios JSON com modo 600 e substituição atômica. Proteger o diretório do projeto contra outros usuários. Inventário e descrições podem ser sensíveis mesmo sem senhas. Configurações/evidências reais são ignoradas pelo Git. O projeto não envia esses arquivos a serviços externos.

## Aplicação e recuperação

Dry-run padrão. Escopo explícito, perfil homologado, limite de interfaces, plano persistido e confirmação são exigidos. --non-interactive é opção explícita apenas para apply. Lock impede duas execuções desta cópia; não coordena diferentes servidores/cópias.

Releitura antes/depois do PATCH reduz risco, mas não elimina corrida entre GET e PATCH. Em falha o lote para; pode haver alterações anteriores confirmadas. Não existe transação global, rollback automático ou garantia de continuidade em queda de energia. Estado sending/unconfirmed exige reconciliação.

## Histórico

Entradas IMC estão desativadas. O legado .disabled é referência inerte, não alternativa operacional. Não restaure scripts antigos em produção. Esta migração não reescreve histórico Git nem atesta rotação de qualquer credencial histórica; se houver credenciais previamente expostas, a rotação depende dos responsáveis.

## Gate de homologação

validated=true é uma declaração local, não assinatura criptográfica. O relatório guarda hash do perfil para rastreabilidade. Verifique a versão instalada e a semântica de cada campo antes de ativar; fixtures não comprovam produção.
