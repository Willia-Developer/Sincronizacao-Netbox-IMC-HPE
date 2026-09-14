# Requisitos de acesso — laboratório e produção

O projeto será apresentado aos responsáveis antes da aplicação no ambiente corporativo. O laboratório testa um switch selecionado. Em produção, lê todo o inventário IMC, compara nomes e atualiza somente interfaces existentes. Devices ausentes no NetBox são descartados e documentados nos logs.

## Servidor de execução

Linux, Python 3.10+, Bash e flock (util-linux). Instale as dependências de requirements.txt em ambiente virtual. Administração do servidor é necessária para provisionamento e instalação de pacotes quando não estiverem disponíveis; a execução usa usuário de serviço sem sudo.

Reserve diretório de aplicação, ambiente virtual, arquivo .env protegido e logs com acesso restrito. Configure DNS, relógio sincronizado, certificados/CA interna e política de retenção dos logs. O script não abre portas de entrada.

## Matriz de comunicação para preencher no chamado

| Origem | Destino | Protocolo | Porta efetiva | Necessidade |
| --- | --- | --- | --- | --- |
| Servidor executor | API do IMC | HTTPS/TCP | Confirmar instalação; padrão do cliente 8443 | Obrigatória nas etapas IMC |
| Servidor executor | API do NetBox | HTTPS/TCP | Definida em NETBOX_URL; 443 sem porta explícita | Obrigatória nas etapas NetBox |
| Servidor executor | DNS corporativo | Conforme serviço DNS corporativo | Confirmar | Quando usar nomes |
| Servidor executor | Serviço de horário corporativo | Conforme infraestrutura | Confirmar | Relógio confiável para logs/TLS |
| Servidor executor | Repositório de dependências ou proxy | HTTPS ou protocolo aprovado | Confirmar | Instalação/atualização; pode usar pacotes offline |
| Estação administrativa | Servidor executor | Acesso administrativo aprovado, por exemplo SSH | Confirmar | Provisionamento/manutenção, não comunicação do sincronizador |

Substituir os destinos e portas por valores reais antes de abrir o chamado. HTTP em laboratório exige configuração explícita e não protege o tráfego; portas incompatíveis são rejeitadas. Em HTTPS, validação TLS é obrigatória e CA interna pode ser configurada por IMC_CA_BUNDLE/NETBOX_CA_BUNDLE.

Se houver proxy, verificar HTTP_PROXY, HTTPS_PROXY e NO_PROXY para as APIs internas. Não é necessário acesso à internet durante execução se dependências e endpoints estiverem disponíveis internamente.

## Permissões das contas

| Serviço / objeto | Leitura | Alteração | Criação/exclusão |
| --- | --- | --- | --- |
| IMC: dispositivos, interfaces e VLANs | GET | Não | Não |
| NetBox: dcim.device | GET | Não | Não |
| NetBox: dcim.interface | GET | PATCH, somente nas etapas de aplicação | Não |
| NetBox: ipam.vlan | GET | Não | Não |

Não é necessário privilégio administrativo global nos produtos. Para os primeiros testes, usar apenas leitura. Depois, conceder ao usuário/token permissão de alteração de interfaces do escopo aprovado. A allowlist de campos é imposta pelo código, não substitui as permissões e restrições do NetBox.

Os campos possíveis são description, mode, untagged_vlan e tagged_vlans. Enabled, status, IP, MAC e dispositivos permanecem fora do fluxo de escrita. Dispositivos, interfaces e VLANs precisam ser provisionados previamente por processo separado.

## Sequência de validação

Seguir o [README oficial](README.md): conexão IMC, descoberta, inspeção do switch, conexão NetBox, comparação, simulação e aplicação controlada. Escolher grupo VLAN se necessário; conferir o significado de ifIndex, PVID e tagged/untagged na instalação real. Hybrid e dados inconclusivos são preservados.

Após aprovação e testes, usar sincronizar_producao.py para todo o inventário. Cada execução é única; instalador cron permanece desativado nesta versão. O bloqueio por flock protege a mesma cópia do projeto, não cópias em servidores distintos.

Credenciais ficam somente no .env protegido. A rotação de credenciais anteriormente expostas precisa de confirmação no sistema de origem; os testes offline não a comprovam.
