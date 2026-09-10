# Segurança e limpeza do histórico

## Ação crítica

Rotacione manualmente a senha iMC anteriormente exposta. Remover arquivos e reescrever commits não revoga a credencial. Revisar também as credenciais NetBox usadas no ambiente; nomes de variável e placeholders não comprovam que um token real foi exposto.

Nenhuma credencial foi testada contra sistemas corporativos.

## Dados removidos

Foram sanitizados exemplos, documentação, PDFs e o script de conexão. O dump interno foi substituído por um aviso. .env, logs, dumps e evidências históricas detalhadas não devem ser publicados.

A auditoria percorre os arquivos atuais e todos os commits alcançáveis. Os resultados completos são gravados em `artifacts/`, ignorado pelo Git. Hashes antigos, valores sensíveis e referências que facilitem localizar as versões comprometidas ficam fora da documentação pública.

## Limpeza histórica

A limpeza é preparada em uma cópia separada com git-filter-repo. Os caminhos com achados são removidos de todos os commits dessa cópia; depois, os arquivos atuais sanitizados são restaurados em um novo commit. O histórico seguro restante pode ser preservado.

Etapas:

1. Guardar backup protegido e cópia sanitizada fora do clone de limpeza.
2. Auditar todos os refs e revisar os caminhos afetados.
3. Executar git-filter-repo com --sensitive-data-removal e --invert-paths.
4. Restaurar os arquivos atuais e validar todos os commits resultantes.
5. Repetir os testes e comparar a árvore candidata com os arquivos revisados.
6. Publicar usando uma condição explícita sobre o hash remoto esperado, para não sobrescrever trabalho novo.
7. Verificar o remoto e orientar colaboradores a usar novos clones.

O arquivo history-paths.txt é uma lista de partida; a auditoria pode identificar caminhos adicionais. Remover um caminho elimina todas as suas versões na cópia filtrada. Por isso, é indispensável preservar e restaurar a versão sanitizada.

## Limites da limpeza

Reescrever refs não garante remoção de caches, forks, clones de terceiros ou referências internas de pull requests. A purga desses objetos pode exigir atendimento do GitHub Support. Não foi aberto chamado de suporte automaticamente.

Após a reescrita, não faça merge ou push de branches baseadas no histórico antigo: isso pode reintroduzir os dados. Prefira novo clone.

Consulte a [orientação oficial do GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## Operação

Use privilégio mínimo, TLS verificado e arquivos locais protegidos. O piloto não cria nem exclui objetos e só altera descrição/VLAN de interfaces existentes. Os testes são offline; conexões ao laboratório precisam de autorização operacional.
