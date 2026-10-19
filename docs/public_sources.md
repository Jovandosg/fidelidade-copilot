# Fontes públicas e metadados

A base entregue neste MVP é sintética. As fontes abaixo orientam a calibração e o desenho dos contratos; nenhuma linha de cliente real foi ingerida.

## ANAC — microdados de tarifas aéreas comercializadas

- URL: https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas/microdados-de-tarifas-aereas-comercializadas
- Formato/distribuição: arquivos para download; a página descreve dados em CSV.
- Cobertura: tarifas domésticas retroativas até 2002 e internacionais até 2011, conforme a página consultada em 14/10/2026.
- Campos relevantes: ano/mês da venda, empresa, aeroportos de origem/destino, tarifa e assentos comercializados.
- Limitação: o registro doméstico cobre passagens do público adulto em geral e corresponde a cerca de 50% do movimento de passageiros pagos; não deve ser tratado como base de clientes.

## ANAC — histórico de voos / Voo Regular Ativo (VRA)

- URL: https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas/historico-de-voos
- Distribuição: formulário de consulta e arquivos mensais CSV.
- Conteúdo: voos de empresas de transporte aéreo, horários de ocorrência e cancelamentos; a página também informa os códigos DI e Tipo Linha.
- Uso proposto: enriquecer rotas, sazonalidade e sinais operacionais na camada raw/treated.

## ANAC — Portal de Dados Abertos

- URL: https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos
- Papel: área concentradora de dados sob responsabilidade da agência, com arquivos e metadados por área de atuação.
- Uso proposto: localizar versões e metadados oficiais sem acoplar a aplicação a um arquivo específico.

## Azul Fidelidade — referência pública de produto

- Programa: https://www.voeazul.com.br/br/pt/programa-fidelidade/conheca-o-programa
- Níveis: https://www.voeazul.com.br/br/pt/programa-fidelidade/niveis
- Observação: as páginas públicas listam os níveis Azul Fidelidade, Topázio, Safira, Diamante e Diamante Unique e descrevem benefícios, trechos e pontos qualificáveis. A implementação usa esses nomes somente como referência de regras de produto; critérios e benefícios podem mudar e devem ser versionados antes de uso real.

## Governança

- Data de consulta: 2026-10-14.
- Frequência sugerida de atualização: mensal para ANAC e revisão a cada alteração de regulamento para o programa.
- Licença/termos: verificar os termos de cada fonte antes de redistribuir arquivos baixados.
- Privacidade: não coletar PII; manter IDs anonimizados; remover campos não necessários para a decisão; revisar viés e explicabilidade antes de ativação.
