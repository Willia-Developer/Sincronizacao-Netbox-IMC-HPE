# Arquitetura do projeto

## Fase 1 - implementada em código, pendente de homologação

WhatsUp Gold -> script Python -> NetBox. O script lê ambos para comparação; escreve exclusivamente campos autorizados de interfaces NetBox. Fonte, regras e cliente de destino são separados em módulos.

## Componentes futuros, fora desta entrega de código

NetBox -> API intermediária -> dashboard HTML: visualização do inventário e evidências. Não foi criado dashboard nem serviço web nesta migração. Não expor tokens no JavaScript do navegador. Qualquer futura edição pelo dashboard exige escopo próprio.

NetBox + Sumos -> serviço de coleta -> SQL central -> regras de conciliação -> API -> dashboard HTML. A instância SQL armazena os dados; coleta e execução precisam de serviço/jobs. Não foi implementado conector Sumos ou banco central nesta entrega.

A conciliação futura precisa de identificador comum, regras de equivalência técnica/comercial, horários de observação, registros duplicados e responsáveis por divergência. Serviço ativo não prova cobrança devida. O relatório deve preservar origem e valores de cada sistema.

O IMC foi retirado do fluxo operacional. As antigas propostas de auditoria WUG x IMC não são o escopo vigente. A numeração das demais entregas deverá ser definida no planejamento; a fase 1 vigente é a sincronização WUG -> NetBox.
