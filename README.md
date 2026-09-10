# Piloto HPE iMC → NetBox

O HPE iMC é a única fonte da verdade. O piloto compara e sincroniza somente **descrição e configuração de VLAN das interfaces existentes**.

- iMC: exclusivamente GET, inclusive autenticação. Logout não envia DELETE.
- NetBox: GET e PATCH de interface individual. POST, PUT e DELETE bloqueados antes da rede.
- Campos possíveis: `description`, `mode`, `untagged_vlan`, `tagged_vlans`.
- Nenhum dispositivo é atualizado; nenhum objeto é criado ou excluído.
- `enabled`, status, up/down, tipo, IP, MAC e demais campos são ignorados.
- Dispositivos, interfaces e VLANs devem existir previamente.
- Nomes devem corresponder exatamente. Ausência ou ambiguidade gera pendência.
- Dry-run é o padrão; não há PATCH sem diferença.
- Logs estão ativos desde o início, com mascaramento e rotação.

A automação continua realizando consultas GET, mas não envia PATCH quando não há diferenças.

## Uso

Após configurar o ambiente conforme [instalação](COMO_INSTALAR_E_TESTAR.md):

```bash
python3 sincronizacao_imc_netbox.py
python3 sincronizacao_imc_netbox.py --dry-run
python3 sincronizacao_imc_netbox.py --apply
python3 sincronizacao_imc_netbox.py --apply --non-interactive
```

`--apply` apresenta o plano completo e solicita confirmação `SIM` em terminal. O modo não interativo exige as duas opções explícitas. Não execute contra sistemas corporativos sem autorização operacional.

## Documentação

- [Contrato técnico e endpoints](SINCRONIZACAO_IMC_NETBOX.md)
- [Instalação e validação local](COMO_INSTALAR_E_TESTAR.md)
- [Segurança e limpeza histórica](docs/SEGURANCA.md)
- [Relatório de auditoria e correções](docs/RELATORIO_FINAL.md)
- [Mapa de arquivos](LISTA_DE_ARQUIVOS.md)

Os PDFs são derivados dos Markdown pelo script `scripts/render_pdfs.py`. Não há PPTX no repositório auditado.
