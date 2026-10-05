# Plano de implantação da fase 1

Objetivo: ler WhatsUp Gold e atualizar campos autorizados de interfaces existentes no NetBox. Não há caminho inverso de escrita.

## Etapas e aceite

1. Preparação: TI/infra disponibiliza servidor, venv, URLs, CA e contas. Aceite: testes GET WUG e NetBox funcionam, sem alteração de inventário.
2. Contrato da fonte: responsável WUG e equipe de rede identificam API de portas físicas, descrição, paginação e VLAN. Aceite: amostras sanitizadas e correspondência com switch piloto registradas.
3. Perfil e identidade: equipe de integração define grupo, nomes/maps e campos habilitados. Aceite: não há colisões; cada campo tem significado confirmado.
4. Simulação: comparar um switch e revisar relatório. Aceite: diferença anterior/proposta compreendida, ausência/null preservados, nenhuma mutação WUG.
5. Aplicação de laboratório: perfil homologado, plano limitado e confirmação. Aceite: NetBox confere com valores propostos e novo dry-run não repete alterações confirmadas.
6. Homologação ampliada: incluir amostra de modelos/stacks/modos de porta. Aceite: paginação, falhas e ambiguidades têm tratamento validado.
7. Produção controlada: aumentar grupo e limite gradualmente. Aceite: responsáveis aprovam escopo, execução e recuperação. Agendamento somente depois dessa decisão.

Prazos dependem da disponibilidade das APIs e das equipes; esta entrega não fixa datas fictícias. Desenvolvimento do código não equivale à implantação concluída.

## Responsabilidades

Equipe de rede valida dados de switch. Administração WUG fornece API e conta de leitura. Administração NetBox mantém cadastro e permissões. Integração mantém mapeamentos/testes/execução. Responsável pela mudança aprova aplicação e define atendimento a falhas.
