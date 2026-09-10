# Relatório do piloto e preparação da publicação

## Resultado técnico

O fluxo ativo usa o iMC como única fonte da verdade e altera somente descrição/VLAN das interfaces existentes no NetBox.

- iMC: exclusivamente GET, inclusive autenticação; logout local, sem DELETE.
- NetBox: GET e PATCH de interface individual.
- Allowlist: description, mode, untagged_vlan, tagged_vlans.
- Nenhum objeto é criado/excluído; nenhum dispositivo é atualizado.
- Enabled, status, up/down, tipo, IP, MAC e demais campos são ignorados.
- Dry-run padrão; --apply exige opção explícita e confirmação, salvo --non-interactive também explícito.
- Planejamento completo, payload mínimo, releitura antes do PATCH e resumo final.
- Configuração validada, TLS/CA interna, logs com rotação/mascaramento e flock.
- Código antigo de criação preservado em arquivo .disabled, bloqueado e fora dos imports.

## Testes e segurança

A suíte offline passou com 74 testes. Foram verificados compilação Python, sintaxe dos três scripts Bash, dependências, análise AST, links locais, cinco PDFs e whitespace do diff.

A demonstração mockada consultou um dispositivo e uma interface, planejou um PATCH de descrição/VLAN e enviou zero PATCHes. Nenhum teste acessou o iMC ou NetBox corporativo.

O resumo publicável da validação está em [VALIDACAO.md](VALIDACAO.md). Resultados completos podem ser regenerados com `python3 scripts/validate.py`; saídas e logs locais ficam em `artifacts/` e `logs/`, ignorados pelo Git.

Foram identificados dados de credencial/configuração, endereçamento e inventário no conteúdo anterior. Exemplos, documentação, PDFs, teste de conexão e dump foram sanitizados. A busca dos valores históricos identificados não encontrou resíduos na versão corrigida; buscas por padrões não garantem ausência absoluta de todo segredo possível.

**Rotacionar manualmente a senha iMC exposta.** Nenhuma limpeza Git substitui a rotação.

## Preparação para GitHub

A publicação da versão corrigida e a limpeza histórica foram autorizadas pelo responsável. O procedimento usa backup protegido, clone isolado, git-filter-repo, restauração dos arquivos sanitizados e validação do histórico resultante.

Os identificadores antigos e manifestos detalhados não fazem parte da documentação pública. Não incluir backups nem branches antigas na publicação.

A branch de destino é main. A atualização deve conferir o hash remoto esperado e não sobrescrever alterações de terceiros. O resultado da publicação deve ser confirmado diretamente no remoto; preparar uma cópia limpa não significa que caches e objetos antigos já tenham sido purgados pelo GitHub.

Procedimento e limites em [SEGURANCA.md](SEGURANCA.md).

## Documentação e arquivos

O contrato completo, endpoints, parâmetros e regras de normalização estão em [SINCRONIZACAO_IMC_NETBOX.md](../SINCRONIZACAO_IMC_NETBOX.md).

O mapa de responsabilidades está em [LISTA_DE_ARQUIVOS.md](../LISTA_DE_ARQUIVOS.md). A relação de arquivos da correção está em [ARQUIVOS_ALTERADOS.md](ARQUIVOS_ALTERADOS.md).

Os cinco PDFs foram regenerados dos Markdown. Não há PPTX no repositório auditado. Cronograma documentado: preparação 1 dia, análise 1 dia, desenvolvimento 5 dias e testes 2 dias; total de 9 dias úteis.

## Pendências operacionais

1. Rotacionar credenciais expostas antes do teste de laboratório.
2. Confirmar endpoints, paginação e semântica de VLAN na versão do iMC instalada.
3. Hybrid sem classificação inequívoca, trunk sem PVID e múltiplas VLANs untagged permanecem bloqueados.
4. VIDs duplicados no NetBox são ambíguos até existir regra operacional explícita de site/grupo.
5. Dispositivos, interfaces e VLANs devem existir previamente.
6. A releitura antes do PATCH reduz conflitos, mas não elimina a janela entre GET e PATCH.
7. O flock coordena processos na mesma cópia; não coordena servidores ou clones distintos.
8. Caches, forks e clones antigos exigem tratamento separado. O GitHub Support pode ser necessário.
9. Agendamento permanece desativado até validação manual.
