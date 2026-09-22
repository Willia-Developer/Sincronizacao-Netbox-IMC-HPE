# WhatsUp Gold ↔ iMC — auditoria de inventário

**Fase posterior à integração iMC → NetBox. Estado: planejamento, sem conectores ou comparação operacional implementados.** Preparação elaborada em 22/09/2026 sobre o commit `065e887`.

O objetivo é verificar se WhatsUp Gold e iMC representam os mesmos dispositivos e se os dados comparáveis concordam. A auditoria deverá apresentar dispositivos exclusivos de cada sistema, diferenças por campo, possíveis duplicidades e informações que não puderam ser verificadas.

Concordância entre dois cadastros não comprova, sozinha, a configuração física atual: ambos podem estar desatualizados. A validação real precisará de coletas completas, datas de observação e conferência de uma amostra com a equipe responsável pelos equipamentos.

## Separação dos projetos

| Projeto | Responsabilidade | Efeito nos sistemas |
| --- | --- | --- |
| `imc/` | Integração iMC → NetBox já existente | Consulta e PATCH autorizado de descrição/VLAN de interfaces |
| `whatsup_gold_imc/` | Futura auditoria WhatsUp Gold ↔ iMC | Leitura de inventários e geração de relatórios; sem correção automática |

NetBox não será uma terceira fonte nesta primeira auditoria. O fluxo atual não dependerá do WhatsUp Gold. A conclusão operacional da integração iMC–NetBox continua sendo uma etapa própria; testes offline não significam implantação concluída.

Todos os scripts, testes, configurações e resultados futuros desta auditoria ficarão nesta pasta. Não importar `imc/sync.py`, `imc/etapas.py`, `imc/runtime.py` ou o cliente legado: eles carregam decisões específicas da sincronização, inclusive possibilidades de escrita. O futuro coletor iMC será um adaptador de leitura independente. Um compartilhamento posterior de biblioteca exigirá revisão própria, sem acoplar as duas CLIs.

## O que está preparado

- [Revisão do projeto atual](ANALISE_PROJETO_ATUAL.md): cobertura, resultados e limites confirmados.
- [Contrato de comparação](CONTRATO_COMPARACAO.md): identidade, campos, atualização e classificação dos resultados.
- [Parametrização futura](PARAMETRIZACAO.md): dados a levantar e contratos das APIs a validar.
- [Plano de execução e aceite](PLANO_VALIDACAO.md): etapas e cenários necessários para validar a comparação real.
- [Exemplo de parâmetros](config/parametros.example.json): proposta de configuração, desativada e sem endereços ou credenciais reais.

O arquivo JSON é uma especificação inicial. Nenhum programa o consome ainda; seus limites serão garantidos somente quando houver implementação e testes. Não existe comando de conexão, coleta, comparação ou aplicação para executar nesta fase.

## Estrutura futura prevista

```text
whatsup_gold_imc/
  config/                exemplos versionados; configuração real ignorada
  src/                   adaptadores de leitura, normalização e comparação
  scripts/               entradas próprias de coleta e relatório
  tests/                 testes próprios e amostras sintéticas
  dados/                 coletas reais locais, ignoradas pelo Git
  relatorios/            resultados reais locais, ignorados pelo Git
  logs/                  execução local, ignorada pelo Git
```

`src/`, `scripts/` e `tests/` são responsabilidades planejadas, não módulos já entregues. As pastas de dados só serão criadas quando necessárias. A proteção Git já está definida em [.gitignore](.gitignore).

## Primeira entrega operacional futura

Começar com um escopo explícito de switches: presença nos dois inventários, nome técnico e IP de gerenciamento. Fabricante, modelo, serial e localização entram conforme disponibilidade e significado dos campos nas versões instaladas. Interfaces, VLANs e estado operacional serão habilitados em etapas próprias após validar os contratos; um dado não disponível deve aparecer como inconclusivo, nunca como igual.

O resultado será uma auditoria com evidência por campo. Não haverá eleição automática do sistema “correto” nem atualização de um produto a partir do outro.

## Próximas informações necessárias

Versões/builds dos dois produtos, Swagger/API efetivamente disponível, escopo de dispositivos, permissões de leitura e exemplos de respostas sanitizados. Credenciais serão configuradas localmente na fase operacional; não devem ser colocadas nestes documentos.
