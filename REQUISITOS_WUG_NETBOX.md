# Requisitos, acessos e permissões

## Servidor de integração

Linux, Python 3.10+, venv e pip. Dependência operacional: requests. pytest é apenas para desenvolvimento; reportlab apenas para PDFs. Git é útil para atualização e revisão, mas o programa também funciona em uma cópia extraída do projeto.

Conta local precisa ler configuração/CA, escrever logs/relatórios e criar lock na raiz. Use um diretório privado. Execute sempre pela venv; não altere Python global do servidor.

## WhatsUp Gold

Levantar versão/build, endereço real da API, Swagger, grupo do piloto, disponibilidade de portas físicas/descrição/VLAN e limitações de paginação. Criar conta dedicada com permissões de leitura conforme recursos da versão instalada. Token pode ser fornecido diretamente ou obtido com usuário/senha via POST token.

Não conceder ao processo a finalidade de alterar monitoramento, inventário, comentários, polling, descoberta ou configuração WUG. O código bloqueia mutações de inventário. Confirme as permissões também no servidor; política local não substitui controle de acesso da aplicação.

## NetBox

Conta/token com leitura de devices, interfaces e VLANs; alteração de interfaces apenas quando habilitar aplicação. Não requer criar/excluir objetos. Restrições por campos são garantidas pelo cliente; verifique permissões e escopo de objetos no NetBox instalado. Um token de consulta pode ser usado durante preparação, substituído por um token adequado no piloto de escrita.

Dispositivos, interfaces e VLANs já devem existir. Definir grupo de VLAN quando houver VIDs repetidos.

## Rede

Autorizar servidor de integração -> host/porta HTTPS WUG e NetBox configurados. Não presumir que ambos usem 443; a documentação WUG apresenta 9644 como exemplo, e a porta efetiva depende da instalação. DNS deve resolver os hosts via resolvedores corporativos autorizados. Proxy, quando necessário, é HTTPS_PROXY_URL explícito.

Para instalar dependências: acesso ao repositório Python autorizado pela empresa e seus hosts de distribuição, normalmente via HTTPS/proxy. Não requer acesso direto ao banco dos produtos. Não instalar regras de firewall automaticamente.

## Informações para iniciar

URLs reais, CA, conta WUG/token, token NetBox, versão/build, nome/ID do switch piloto, grupo WUG, grupo VLAN NetBox e amostras sanitizadas de resposta. Configure credenciais apenas localmente. Não registrar senhas no Git, docs, prints ou chamados.
