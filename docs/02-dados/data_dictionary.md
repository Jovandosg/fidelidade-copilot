# Dicionário de dados

| Campo | Camada/tabela | Tipo | Obrigatório | Definição e uso |
|---|---|---:|:---:|---|
| `customer_id` | todas | string | sim | Identificador sintético anônimo; não é CPF, e-mail ou ID real. |
| `signup_date` | raw/customers | date | sim | Data sintética de entrada no programa. |
| `loyalty_tier` | raw/customers | string | sim | Nível simulado inspirado nos níveis públicos: Azul Fidelidade, Topázio, Safira, Diamante e Diamante Unique. |
| `home_airport` | raw/customers | string | sim | Aeroporto-base sintético/plausível em código IATA. |
| `preferred_channel` | raw/customers | string | sim | Canal sintético predominante de compra. |
| `transaction_id` | raw/transactions | string | sim | Chave única do evento de compra. |
| `flight_date` | raw/transactions | date | sim | Data sintética do voo no período de 12 meses. |
| `origin`, `destination` | raw/transactions | string | sim | Origem e destino do trecho em código IATA. |
| `amount_brl` | raw/transactions | decimal | sim | Tarifa simulada em reais; não inclui taxas auxiliares. |
| `qualifying_points` | raw/transactions | integer | sim | Pontos qualificáveis simulados para análises de progressão. |
| `cancelled` | raw/transactions | boolean | sim | Indicador sintético de cancelamento. |
| `trips_12m` | analytics/customer_features | integer | sim | Quantidade de transações não canceladas nos últimos 12 meses. |
| `spend_12m_brl` | analytics/customer_features | decimal | sim | Soma de tarifas não canceladas. |
| `avg_ticket_brl` | analytics/customer_features | decimal | sim | Gasto médio por viagem não cancelada. |
| `recency_days` | analytics/customer_features | integer | sim | Dias desde a última viagem até 30/09/2026. |
| `preferred_route` | analytics/customer_features | string | sim | Rota mais frequente do cliente. |
| `value_score` | analytics/customer_features | decimal | sim | Score 0–100, combinação normalizada de frequência, gasto, recência e tier. |
| `segment` | analytics/customer_features | string | sim | Segmento acionável para o MVP. |
| `recommended_action` | analytics/customer_features | string | sim | Próxima ação explicável, derivada do segmento e do sinal de recência/valor. |

## Regras de qualidade

As chaves são únicas e não nulas. Datas devem estar no período do contrato. Tarifas e pontos não podem ser negativos; origem e destino não podem coincidir; `value_score` fica entre 0 e 100. A tabela analítica deve ter exatamente 1.200 clientes.
