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
| `points_balance` | raw/customers | integer | sim | *(v1.1.0)* Saldo sintético de pontos; base para risco de expiração e NBA de resgate. |
| `is_corporate` | raw/customers | boolean | sim | *(v1.1.0)* Perfil corporativo sintético (sem identificar empresa). |
| `primary_cabin` | raw/customers | string | sim | *(v1.1.0)* Cabine predominante: `economy`, `premium` ou `business`; define a taxa de margem simulada. |
| `margin_brl` | raw/transactions | decimal | sim | *(v1.1.0)* Margem simulada do voo (0 se cancelado; reduzida em 30% se houve disrupção). Insumo do HVS. |
| `delay_minutes` | raw/transactions | integer | sim | *(v1.1.0)* Atraso simulado, 0–600 min (0 quando cancelado). |
| `disrupted` | raw/transactions | boolean | sim | *(v1.1.0)* Voo irregular: cancelado **ou** atraso ≥ 60 min. Derivado de `cancelled`/`delay_minutes` e validado no pipeline. |
| `complaint_flag` | raw/transactions | boolean | sim | *(v1.1.0)* Reclamação simulada associada ao voo (muito mais provável quando `disrupted`). |
| `route` | analytics/route_metrics | string | sim | *(v1.1.0)* Chave `ORIGEM-DESTINO` (IATA). |
| `flights`, `disrupted_flights`, `complaints` | analytics/route_metrics | integer | sim | *(v1.1.0)* Voos, voos irregulares e reclamações da rota (inclui cancelados). |
| `avg_delay_minutes`, `revenue_brl` | analytics/route_metrics | decimal | sim | *(v1.1.0)* Atraso médio e receita (voos não cancelados) da rota. |
| `ivr` | analytics/route_metrics | decimal | sim | *(v1.1.0)* Índice de Volatilidade da Rota, 0–100 = % de voos irregulares (`disrupted_flights / flights × 100`). |
| `trips_12m` | analytics/customer_features | integer | sim | Quantidade de transações não canceladas nos últimos 12 meses. |
| `spend_12m_brl` | analytics/customer_features | decimal | sim | Soma de tarifas não canceladas. |
| `avg_ticket_brl` | analytics/customer_features | decimal | sim | Gasto médio por viagem não cancelada. |
| `recency_days` | analytics/customer_features | integer | sim | Dias desde a última viagem até 30/09/2026. |
| `preferred_route` | analytics/customer_features | string | sim | Rota mais frequente do cliente. |
| `value_score` | analytics/customer_features | decimal | sim | Score 0–100, combinação normalizada de frequência, gasto, recência e tier. |
| `segment` | analytics/customer_features | string | sim | Segmento acionável para o MVP. |
| `recommended_action` | analytics/customer_features | string | sim | Próxima ação explicável, derivada do segmento e do sinal de recência/valor. |
| `points_balance` | analytics/customer_features | integer | sim | *(v1.1.0)* Saldo de pontos herdado de `customers`. |
| `margin_12m_brl` | analytics/customer_features | decimal | sim | *(v1.1.0)* Soma de `margin_brl` dos voos não cancelados. |
| `disruptions_12m` | analytics/customer_features | integer | sim | *(v1.1.0)* Voos irregulares do cliente (cancelados ou atraso ≥ 60 min). |
| `complaints_12m` | analytics/customer_features | integer | sim | *(v1.1.0)* Reclamações do cliente no período. |
| `hvs_clv` | analytics/customer_features | decimal | sim | *(v1.1.0)* Componente de valor (0–100): 70% percentil de gasto + 30% percentil de viagens. |
| `hvs_margin` | analytics/customer_features | decimal | sim | *(v1.1.0)* Componente de margem (0–100): percentil de `margin_12m_brl`. |
| `hvs_stability` | analytics/customer_features | decimal | sim | *(v1.1.0)* Componente de estabilidade (0–100): 60% recência + 40% regularidade (viagens/8, teto 1). |
| `hvs_cost_to_serve` | analytics/customer_features | decimal | sim | *(v1.1.0)* Proxy de custo de servir (0–100): 60% disrupções (teto 4) + 40% reclamações (teto 2). |
| `hvs` | analytics/customer_features | decimal | sim | *(v1.1.0)* High-Value Score = clip(0,4·clv + 0,3·margem + 0,3·estabilidade − 0,2·custo, 0, 100). Pesos em `src/models/hvs.py`. |
| `profile` | analytics/customer_features | string | sim | *(v1.1.0)* Perfil A–E por faixa de HVS (A ≥ 75, B ≥ 60, C ≥ 45, D ≥ 30, E abaixo). |
| `risk_score` | analytics/customer_features | decimal | sim | *(v1.1.0)* Probabilidade estimada (×100) de não voar nos próximos 90 dias; GradientBoosting, avaliado em hold-out temporal. |
| `risk_drivers` | analytics/customer_features | string | sim | *(v1.1.0)* Até 3 fatores que mais elevam o risco do cliente (efeito de trocar cada variável pela mediana). |
| `nba_action` | analytics/customer_features | string | sim | *(v1.1.0)* Ação com maior margem esperada líquida; `Monitorar (sem acao)` se nenhuma compensar. |
| `nba_expected_margin_brl` | analytics/customer_features | decimal | sim | *(v1.1.0)* P(churn) × uplift assumido × margem 12m − custo da ação (0 se monitorar). Premissas sintéticas. |
| `nba_requires_approval` | analytics/customer_features | boolean | sim | *(v1.1.0)* `true` quando a ação custa mais de R$ 10: exige aprovação humana antes de qualquer disparo. |

> Métricas dos modelos em `data/analytics/model_metrics.json`. Com dados sintéticos elas descrevem o gerador, não uma previsão validada.

> Todos os dados são **sintéticos** (`synthetic: true` no contrato): sem PII e sem relação com clientes reais da Azul.

## Regras de qualidade

As chaves são únicas e não nulas. Datas devem estar no período do contrato. Tarifas e pontos não podem ser negativos; origem e destino não podem coincidir; `value_score` fica entre 0 e 100; `ivr` entre 0 e 100. `disrupted` deve ser coerente com `cancelled`/`delay_minutes`, a margem não pode exceder a tarifa e `route_metrics.flights` soma o total de transações. A tabela analítica tem exatamente um registro por cliente (o número de clientes não é fixo no código).
