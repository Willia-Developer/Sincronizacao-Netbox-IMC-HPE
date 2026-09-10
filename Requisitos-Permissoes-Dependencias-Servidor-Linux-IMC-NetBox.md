# Requisitos do servidor do piloto

Linux com Python 3.10+, Bash, flock e ambiente virtual. Instalar somente as dependências em requirements.txt. Não requer acesso administrativo para executar a sincronização.

iMC: conta de serviço somente leitura e acesso GET aos endpoints de dispositivos, interfaces e VLANs documentados. NetBox: token para leitura e atualização de interfaces; a aplicação impõe allowlist de description, mode, untagged_vlan e tagged_vlans.

Dispositivos, interfaces e VLANs precisam existir previamente. Nenhum objeto é criado/excluído e nenhum dispositivo é atualizado. Enabled, status, up/down, tipo, IP e MAC são ignorados.

HTTPS com validação de certificado; CA interna configurável. Segredos em arquivo local protegido e ignorado pelo Git. Rotacionar a credencial exposta antes da validação.

Execução manual única, dry-run padrão, aplicação com --apply e confirmação. Logs ativos com rotação e mascaramento. Concorrência bloqueada por flock. Sem cron até validar o piloto.

Cronograma de referência: preparação 1 dia útil; análise 1 dia útil; desenvolvimento 5 dias úteis; testes 2 dias úteis. Total: 9 dias úteis.

Não existe PPTX na árvore auditada; portanto não há slides disponíveis para editar ou avaliar como imagens. O escopo acima deve orientar eventual apresentação futura.
