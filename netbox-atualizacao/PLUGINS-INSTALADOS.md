# Plugins do NetBox 4.7.2

Plugins solicitados e versões fixadas:

| Plugin | Versão | Acesso |
|---|---|---|
| NextBox UI | 1.0.7 | `/plugins/nextbox-ui/topology/` |
| NetBox DNS | 1.7.3 | `/plugins/netbox-dns/zones/` |
| NetBox BGP | 0.20.2 | `/plugins/bgp/session/` |
| NetBox Attachments | 12.0.0 | `/plugins/netbox-attachments/netbox-attachments/` |
| NetBox Documents | 0.8.5 | `/plugins/documents/documents/` |
| NetBox Map | 0.12.0 | `/plugins/map/sitemap/` |

Topology Views 4.7.0 e Floorplan 0.10.0 foram preservados.

Instalação concluída em 12/10/2026. Backup anterior: `<DIRETORIO_NETBOX>/backups/pre-requested-plugins-20261012-175343`.

Validação: migrações concluídas, nenhuma migração pendente, `manage.py check` sem problemas, aplicação e worker saudáveis, login HTTP 200 e páginas autenticadas dos plugins, formulários de anexos/documentos, topologias, mapa, dispositivos e sites retornando HTTP 200. Contagens preservadas: 111 dispositivos, 11 sites e 1 rack. Evidência: `plugin-install/validation-production.txt`. Não foi executado um upload real de documento ou anexo.

Secrets/Secret Store está pendente: NetBox Secrets 3.1.1 suporta somente NetBox 4.6; não há release compatível com 4.7. A NetBox Labs retirou sua certificação em 22/09/2026 devido a um aviso público de segurança sem correção. Não foi instalado nem habilitado.

Referências: https://github.com/Onemind-Services-LLC/netbox-secrets e https://netboxlabs.com/docs/enterprise/nbe-release-notes/.

## Imagem e manutenção

Imagem: `netbox-local:4.7.2-all-plugins`. Configuração persistente em `configuration/plugins.py`, pacotes em `plugin_requirements.txt` e construção em `Dockerfile-Plugins`.

As dependências atuais do NetBox foram preservadas por `plugin-install/constraints.txt`. O script `plugin-install/patch-nextbox.py` contém duas adaptações reproduzíveis aplicadas durante o build:

- NextBox UI: remover apenas o sufixo Docker ao interpretar a versão do NetBox com `packaging.version`, inclusive na migração inicial.
- Documents: substituir o dicionário antigo de ações pelos objetos `BulkExport` e `BulkDelete` da API do NetBox 4.7, preservando as permissões.

Revisar essas adaptações quando atualizar os plugins ou o NetBox. Secrets não deve ser habilitado até existir uma versão corrigida e compatível.

## Uso

Attachments adiciona a aba de anexos a dispositivos, sites, circuitos e outros objetos dos aplicativos dcim, circuits, ipam, tenancy, virtualization e wireless. Documents oferece documentos e links externos associados a objetos.

NextBox UI usa filtros para selecionar os dispositivos que aparecerão na topologia. Os sites precisam de coordenadas para aparecerem no mapa geográfico. Plantas baixas e posições dos objetos são cadastradas no NetBox Map.

Os usuários comuns precisam receber as permissões dos novos modelos; nenhuma permissão extra foi concedida automaticamente.

## Backup e reversão

O caminho do backup anterior à ativação está em `plugin-install/latest-backup-path.txt`. Ele contém o banco em formato pg_dump, media, configuração, arquivos env e arquivos de construção. A imagem anterior foi preservada localmente.

Para voltar à configuração anterior, parar aplicação e worker, recuperar os arquivos do backup e iniciar a imagem anterior. As novas tabelas dos plugins podem ficar no banco, pois as migrações não alteram o schema dos aplicativos anteriores. Para restauração integral, restaurar o banco e media do backup com aplicação e worker parados; isso perde as alterações posteriores ao backup.

## Passo a passo de manutenção

Consulte [MANUTENCAO-NETBOX-E-PLUGINS.md](MANUTENCAO-NETBOX-E-PLUGINS.md) para reconstruir a instalação dos oito plugins, atualizar o NetBox, fazer backup e recuperar após falhas. Versões e ativação conferidas no contêiner em 14/10/2026.
