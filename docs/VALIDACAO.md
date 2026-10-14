# Validação offline

> Relatório histórico da base anterior. Para a entrega por etapas, consulte [VALIDACAO_ETAPAS.md](VALIDACAO_ETAPAS.md).

Versão corrigida do piloto: 74 testes aprovados.

| Verificação | Resultado |
| --- | --- |
| pytest -v | 74 passed |
| python3 -m compileall . | PASS |
| bash -n para cada script de imc/ | PASS |
| pip check | PASS |
| Análise estática AST dos clientes ativos | PASS |
| Links locais e extração dos cinco PDFs | PASS |
| git diff --check | PASS |
| Dry-run sintético | 1 proposta, zero PATCHes |

A suíte usa mocks e um bloqueio global de transporte HTTP real.

## Cobertura

- Métodos HTTP e bloqueio de requisições diretas/preparadas.
- Allowlist, tipos de payload e bloqueio integral de campos desconhecidos.
- Objetos inexistentes, nomes exatos e resultados ambíguos.
- Descrição ausente, nula, vazia ou inválida.
- VLANs ausentes, inválidas, duplicadas, desordenadas e paginação incompleta.
- Payloads mínimos e nenhuma atualização quando os dados são iguais.
- Dry-run, aplicação explícita, confirmação e releitura antes do PATCH.
- Estado up/down ignorado; criação legada bloqueada.
- Credenciais, TLS, URLs, logs protegidos e concorrência.

## Reprodução

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python3 scripts/validate.py
python3 scripts/audit_security.py
```

As saídas detalhadas são locais e ficam em artifacts/. Não há dependência de sistemas corporativos.
