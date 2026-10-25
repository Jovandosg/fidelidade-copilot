> Usando as Skills de Caveman, eu estou com esse projeto para um hackathoon para fazer e estou com as responsabilidades da pessoa 3 que no caso é a montagem do agent do sistema com sua
  harness e sujas guardrails para que ele esteja bem alinhado com a proposta do projeto, quero que vc analise todos os docs do projeto para que assim vc consiga organizar o maximo de
  contexto e entenda as regras de negócio e entender melhor o desafio. tal desafio é DESAFIO 3 — AZUL · CRM de Alto Valor

  Clientes de alto valor voam com frequência, geram maior margem e sustentam o programa de fidelidade. Retê-los custa menos do que conquistar novos — e protege a receita das rotas mais
  rentáveis. O desafio de vocês é entregar um MVP que identifique perfis de clientes de alto valor a partir de dados públicos e proponha uma estratégia de CRM para fidelizá-los, com dados
  e IA no centro da solução. 📎 O briefing completo está no documento em anexo, com o contexto detalhado, as fontes públicas sugerida

  Clientes de alto valor voam com frequência, geram maior margem e sustentam o programa de fidelidade. Retê-los custa menos do que conquistar novos — e protege a receita das rotas mais
  rentáveis.
  O desafio de vocês é entregar um MVP que identifique perfis de clientes de alto valor a partir de dados públicos e proponha uma estratégia de CRM para fidelizá-los, com dados e IA no
  centro da solução.
  📎 O briefing completo está no documento em anexo, com o contexto detalhado, as fontes públicas sugeridas, a arquitetura esperada e os critérios de avaliação. Leiam antes da call de
  dúvidas.

○ Thought for 1m 2s (No knowledge file exists yet. The focus shifts to reviewing rules 7 and 8. Specifically, rule 7 dictates that when a prompt initiates a new project, all provided...)
● Ran 2 commands (Get-ChildItem -Recurse -File | Select-Object FullName, Length · Get-ChildItem -Path . -Depth 2 -Exclude .venv, .git | Select-Object FullName)
● Explored 7 files (visao-produto.md, arquitetura.md, sprint-01.md, +4)
… 16 more actions (11 reads, 4 commands, 1 task) …
● Ran 3 commands (Get-ChildItem -Path scripts -Recurse -File · Get-ChildItem -Directory | Select-Object Name · Get-ChildItem -Recurse -Filter "*conhec*")
● Edited 1 file (conhecimentos.md) (ctrl+o to expand)

▸ Thought for 6s, 403 tokens

  Fiz a varredura completa e análise crítica de toda a documentação, bases de dados e regras de negócio presentes no repositório. Conforme a regra de projeto, consolidei todo esse
  mapeamento detalhado no arquivo de conhecimentos: conhecimentos.md.

  Abaixo está o resumo executivo e técnico do contexto, alinhado à sua responsabilidade como Pessoa 3 (Agent, Harness e Guardrails):
  ──────
  ### 1. O Desafio e o Problema de Negócio

  • Objetivo central: Entregar um MVP com dados e IA no centro para identificar clientes de alto valor econômico/comportamental, prever risco de evasão (churn precoce) e recomendar
  estratégias de CRM contextuais (Next Best Action - NBA) para fidelizá-los sem queimar margem.
  • Caso demonstrativo principal do Pitch: O cliente sintético Corporativo em Risco (P1) — cliente de alta receita/score que apresentou queda de frequência e atrito recente (ex.:
  atrasos/reclamações na rota frequente), precisando de uma ação rápida e cirúrgica de reconquista.
  • Restrição de Ouro (HITL): A solução não executa ações autônomas. Toda recomendação requer aprovação humana mandatória (Human-in-the-Loop) antes de qualquer ativação.
  • Parcerias Comerciais: Sugestões de mobilidade, hotelaria e mimos são hipóteses comerciais sujeitas a contrato, disponibilidade e elegibilidade.
  ──────
  ### 2. Cruzamento de Regras de Negócio e Setoriais

  Documentos analisados: Cruzamento de Regras de Negócio - Aéreas.pdf e public_sources.md.

  1. Regulação ANAC (Resolução 400):
      • Arrependimento de compra: Reembolso integral até 24h pós-compra se realizada com 7+ dias de antecedência.
      • Assistência Material por Atrasos: > 1h (comunicação), > 2h (alimentação/vouchers), > 4h ou pernoite (hospedagem e traslado).
      • Bagagem de mão: Até 10 kg (soma de 115 cm na Azul) + item pessoal. Despacho (23 kg) atrelado à tarifa ou status.
  2. Azul Fidelidade (Tiers e Benefícios):
      • Categorias: Azul Fidelidade, Topázio, Safira, Diamante e Diamante Unique.
      • Ações de CRM devem respeitar o patamar do cliente (ex.: cortesia de Espaço Azul, upgrades de cabine, vouchers de parceiros e bônus de pontos qualificáveis).

  ──────
  ### 3. Responsabilidades da Pessoa 3: Arquitetura do Agente

                              [Entrada: Perfil Analítico do Cliente]
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │     Input Guardrail     │
                                │  (Anti-PII & Sanity)    │
                                └────────────┬────────────┘
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │      Agent Harness      │
                                │  (Orquestração & Tools) │
                                └─────┬─────────────┬─────┘
                         Chamada LLM  │             │ Fallback Determinístico
                                      ▼             ▼ (Se LLM offline)
                                ┌─────────────────────────┐
                                │    Output Guardrail     │
                                │ (Pydantic & Compliance) │
                                └────────────┬────────────┘
                                             │
                                             ▼
                                ┌─────────────────────────┐
                                │  Human-in-the-Loop      │
                                │ (Aprovação Obrigatória) │
                                └─────────────────────────┘

  #### A. O Agente (src/agent/)

  • Persona: Especialista de CRM e Retenção da Azul.
  • Função: Receber o perfil (high_value_score, churn_risk, trips_12m, recency_days, preferred_route, atritos e tier), formular o diagnóstico de causa-raiz e prescrever a próxima melhor
  ação de CRM.
  • Tools controladas: Consulta a benefícios por tier, checagem de conformidade ANAC e catálogo de hipóteses de parcerias locais por aeroporto.

  #### B. O Harness (src/agent/harness.py e tests/test_agent.py)

  • Runtime Harness: Injeção de contexto estruturado e fallback determinístico robusto (caso o LLM não responda ou falhe na validação, o motor do transform.py entra em ação
  imediatamente, garantindo que a demo nunca quebre).
  • Evaluation Harness: Bateria de testes automatizados com perfis sintéticos de teste (ex.: cliente corporativo em risco, cliente VIP promotor, cliente lazer oportunidade e cenários de
  tentativa de bypass de regras).

  #### C. As Guardrails (src/agent/guardrails.py)

  • Input Guardrails: Verificação de integridade dos dados e bloqueio de PII.
  • Output Guardrails (Pydantic Model): Validação estrita de formato:
      • customer_id
      • diagnosis (análise de risco e valor)
      • evidence_factors (motivos da prioridade)
      • recommended_action (ação cirúrgica de retenção)
      • partner_hypothesis (parceiro sugerido + disclaimer obrigatório de hipótese)
      • confidence_score (0.0 a 1.0)
      • requires_human_approval (obrigatoriamente True)
  • Compliance Guardrail: Impedir que o modelo sugira descontos abusivos que queimem margem ou invente contratos inexistentes.
  ──────
  ### Próximos Passos

  Tudo está mapeado e documentado no conhecimentos.md. Estamos prontos para implementar os módulos do agente (src/agent/), seus guardrails Pydantic e os testes do harness. Como deseja
  prosseguir?

────────────────────────────────────────────────────────────
> Perfeito tendo envista todas as informações até então analizadas por vc vamos afunilar e focar nas regras de negócios e nas informações salvas nos @[docs] e @[data] quero que vc me
  passe 5 respostas quanto a seguinte pergunta A Azul ja tem certos padrões analisados dos seus clientes mas ela quer saber qual detalhe ainda não foi visto e é um diferencial que deixou
  batido mas que poderia impulcionar as vendas e elevar/aprimorar a qualidade de negócios/viagens/atendimento dos clientes assim podendo até mesmo captar mais pessoas + gostaria que com
  base nessas 5 respostas em cada uma delas vc fizese 7 perguntas bem objetivas de multipla escolha e 7 perguntas Abertas todas com o objetivo de coletar mais KPIs para nosso agente final
  e o porque dessas KPIs selecionadas. quero que a resposta desse prompt seja um arquivo.md na pasta @[docs]

○ Thought for 1m 55s (Initial focus is on identifying unmet customer needs by cross-referencing existing patterns with business rules and documented data. Will extract five distinct,...)
● Edited 1 file (diferenciais_e_kpis_agente.md) (ctrl+o to expand)

▸ Thought for 6s, 151 tokens

  A análise completa foi estruturada e salva no arquivo diferenciais_e_kpis_agente.md.

  Abaixo está a síntese dos 5 diferenciais estratégicos não convencionais levantados a partir do cruzamento entre os dados analíticos, as regras da ANAC e o contexto de negócio da Azul,
  juntamente com a estrutura de coleta de dados para o Agente:
  ──────
  ### Os 5 Diferenciais Estratégicos Identificados

  1. Sinergia "Bleisure" e o Share of Wallet Familiar Oculto:
      • O detalhe que passa batido: O cliente voa corporativo (B2B pago por agências/TMC), mas viaja em lazer e férias com a família (B2C de alta rentabilidade). Tratar esses perfis de
      forma fragmentada perde a conversão de múltiplos assentos de alta margem.
      • Foco de KPIs: leisure_to_corporate_ratio, family_pnr_share, avg_leisure_party_size, bleisure_stay_rate.
  2. Micro-Atritos Acumulados e o "Recovery" Proativo antes do Churn Silencioso:
      • O detalhe que passa batido: Clientes VIP raramente abrem SAC para pequenos atrasos ou mudanças de portão; eles simplesmente migram de companhia após 2 ou 3 eventos de fricção.
      Cumprir apenas a Resolução 400 da ANAC burocraticamente (lanche após 2h) não retém passageiros de alto valor.
      • Foco de KPIs: weighted_friction_index, silent_churn_propensity, recovery_lead_time_hours, recovery_cost_to_margin_ratio.
  3. A Experiência "Porta a Porta" e a Fricção Logística dos Hubs (VCP, CNF, REC):
      • O detalhe que passa batido: A malha e os hubs estruturantes da Azul (especialmente Viracopos) oferecem vantagens operacionais sólidas, mas enfrentam atrito no deslocamento
      rodoviário e estacionamento para executivos de capitais. Conectar a passagem a uma mobilidade terrestre de alto padrão remove a objeção que faz o cliente optar por
      Congonhas/Guarulhos.
      • Foco de KPIs: door_to_door_duration_mins, ground_shuttle_adoption_rate, airport_proximity_risk_index, same_day_return_ratio.
  4. Prevenção Ativa da Perda de Status e a Armadilha do Status Match:
      • O detalhe que passa batido: No segundo semestre, clientes percebem que não conseguirão a requalificação de categoria (Safira/Diamante) para o ano seguinte. Ao antecipar o
      rebaixamento, aceitam campanhas de Status Match de concorrentes (Smiles/LATAM Pass) meses antes do ciclo virar.
      • Foco de KPIs: tier_qualification_gap_pct, run_rate_qualifying_points_per_month, status_match_vulnerability_score, fast_track_completion_rate.
  5. A "Demanda Sombra" (Pesquisas sem Conversão e Desistências em 24h — ANAC 400):
      • O detalhe que passa batido: O CRM convencional analisa transações emitidas, ignorando pesquisas abandonadas e desistências no prazo de arrependimento de 24 horas (art. 11 Res.
      ANAC 400). Esses eventos sinalizam incompatibilidade de horário ou preço descolado da concorrência corporativa antes que o cliente pare de voar.
      • Foco de KPIs: vip_search_to_abandon_ratio, anac_cooling_off_cancellation_rate, shadow_demand_estimated_loss_brl, schedule_mismatch_flag.

  ──────
  ### Conteúdo Detalhado no Documento Gerado

  No arquivo diferenciais_e_kpis_agente.md, cada um dos 5 tópicos acima foi expandido com:

  • 7 Perguntas Objetivas de Múltipla Escolha (totalizando 35 perguntas com 4 alternativas técnicas orientadas a métricas de CRM e aviação).
  • 7 Perguntas Abertas (totalizando 35 perguntas investigativas focadas em processos, dados e regras).
  • Tabela de Mapeamento Técnico de KPIs com o nome da feature no agente, tipagem e a justificativa técnica/negócio para alimentar o harness e os guardrails.
  • Diagrama de Arquitetura de Integração conectando os novos KPIs ao fluxo de Human-in-the-Loop, controle de custos e fallback determinístico do sistema.

────────────────────────────────────────────────────────────
> com base no documento @[docs/diferenciais_e_kpis_agente.md] e todas as informações dele e KPIs analisadas, quero que vc responda as peguntas nesse documento Reflita sobre o
  assunto(pesquise se precisar) e reformule 7

────────────────────────────────────────────────────────────
> com base no documento @docs\diferenciais_e_kpis_agente.md e todas as informações dele e KPIs analisadas, quero que vc responda as peguntas nesse documento Reflita sobre o
  assunto(pesquise se precisar) e reformule 7 perguntas de multipla escolha feitas para uma pesquisa que será ]entregue para os clientes de empresas aérias para que eles respondam e nós,
  como pesquisadores possamos, com base nas respostas deles alimentar as KPIs que foram levantadas no documento e nos dados em @[data]

○ Thought for 48.3s (Considering the user's request, the initial instruction focuses on responding to questions based on a specific document, including reflection and potential extern...)
● Edited 1 file (pesquisa_clientes_kpis.md) (ctrl+o to expand)

  A análise profunda e a formulação do instrumento de pesquisa para os clientes foram salvas em pesquisa_clientes_kpis.md.

  O documento está estruturado em duas etapas:

  1. Reflexão técnica consolidando os dados e regras de negócio da aviação brasileira para responder às dúvidas estratégicas dos 5 diferenciais.
  2. 7 Perguntas de Múltipla Escolha reformuladas diretamente para o cliente final, com o mapeamento exato de como cada resposta alimenta as features e KPIs da base em data/ e a tomada
  de decisão do Agente de CRM.
  ──────
  ### Resumo das 7 Perguntas Reformuladas para os Clientes Finais

   # | Tema Central do Diferenci… | Pergunta Aplicada ao Passageiro                                          | KPI / Feature Alimentada no Agente
  ---|----------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------------
   1 | Sinergia Bleisure &        | Frequência de extensão de viagens de trabalho para lazer ou férias em    | bleisure_stay_rate e family_pnr_share (orienta ofertas de assento e
     | Família                    | família no ano.                                                          | bagagem para acompanhantes)
   2 | Micro-Atritos & Churn      | Reação do cliente após atrasos > 60 min ou alterações de conexão.        | friction_sensitivity_weight e silent_churn_propensity (calibra gatilho P1
     | Silencioso                 |                                                                          | de evasão)
   3 | Recovery Proativo Pós-     | Compensação preferida em caso de imprevisto operacional (pontos          | preferred_recovery_type e recovery_cost_tier (direciona o tipo de NBA com
     | Falha                      | qualificáveis, upgrade, voucher ou atendimento direto).                  | menor queima de margem)
   4 | Jornada Porta a Porta      | Fator decisivo entre voar pelo hub (Viracopos/Confins) versus aeroportos | airport_proximity_risk_index e hub_affinity_score (ativa vouchers de
     | (Hubs)                     | centrais (Congonhas/Santos Dumont).                                      | mobilidade/transfer e estacionamento)
   5 | Defesa contra Status Match | Comportamento no 2º semestre caso perceba risco de rebaixamento de       | status_match_vulnerability e tier_loyalty_resilience (aciona desafios
     |                            | categoria no Azul Fidelidade.                                            | rápidos tipo Fast-Track)
   6 | Demanda Sombra (Buscas sem | Motivo principal de pesquisar voo no canal digital e desistir da compra  | abandon_primary_cause e schedule_friction_weight (ajusta notificações de
     | Conversão)                 | (horário, teto de tarifa corporativa ou falta de assento).               | liberação de assento e rotas)
   7 | Inovação Decisiva de       | Qual inovação única tornaria o cliente exclusivo da Azul (concierge ágil | value_driver_preference e nba_propensity (define o cluster mestre de
     | Fidelidade                 | no app, benefícios familiares, mobilidade ou flexibilidade de status).   | intervenção do Agente)
  ──────
  ### Como as Respostas Conectam ao Trabalho da Pessoa 3 (Agent & Harness)

  1. Camada de Dados (customer_features.parquet):
      • As alternativas escolhidas pelo cliente (A, B, C ou D) são mapeadas para pesos normalizados (0.0 a 1.0) que entram como novas colunas na matriz analítica.
  2. Harness de Decisão (src/agent/):
      • Em vez de usar apenas recência e gasto passado, o Agente agora calcula o score com base no atrito percebido, vulnerabilidade de status e potencial familiar.
  3. Guardrails de Custo:
      • O Agente cruza a preferência declarada do passageiro (ex.: prefere pontos qualificáveis a desconto financeiro) com a margem do cliente, garantindo que o custo da ação de
      retenção permaneça sob limites estritos.


  O detalhamento completo das opções de resposta, pontuações e fluxos de integração está disponível no arquivo pesquisa_clientes_kpis.md.

────────────────────────────────────────────────────────────
> ficou quase perfeito, reformule essas perguntas não só para clientes Azul mas para multiplas empresas aereas.

○ Thought for 39.6s (The user is pleased with the current draft but requests a generalization of the seven multiple-choice questions. The goal is to make the questions applicable to p...)
● Edited 1 file (pesquisa_clientes_kpis.md) (ctrl+o to expand)

  A reformulação foi concluída com sucesso! Atualizei o documento pesquisa_clientes_kpis.md com as 7 perguntas de múltipla escolha 100% agnósticas de companhia aérea, permitindo sua
  aplicação direta a passageiros frequentes de qualquer operadora (Azul, GOL, LATAM, companhias internacionais).
  ──────
  ### Visão Geral do Instrumento de Pesquisa Multicompanhias

  1. Pergunta 1 — Sinergia Bleisure & Família:
      • Foco no Passageiro: Frequência com que aproveita viagens de trabalho para estender o fim de semana ou viaja a lazer com acompanhantes.
      • Alimentação no Pipeline: Gera bleisure_stay_rate e family_pnr_share, permitindo ao Agente identificar o potencial de conversão de múltiplos assentos B2C de alta rentabilidade.
  2. Pergunta 2 — Impacto de Imprevistos & Churn Silencioso:
      • Foco no Passageiro: Reação pós-atraso superior a 60 min ou perda de conexão (se releva, se continua normalmente, se passa a cotar concorrentes ou se abandona a empresa).
      • Alimentação no Pipeline: Alimenta friction_sensitivity_weight e silent_churn_risk, calibrando o multiplicador de atrito sobre o score de evasão.
  3. Pergunta 3 — Modelo de Recuperação de Confiança (Recovery Proativo):
      • Foco no Passageiro: Qual atitude pós-falha gera maior sensação de valor (pontos qualificáveis de status, upgrade de assento/lounge, voucher financeiro ou comunicação
      transparente sem burocracia).
      • Alimentação no Pipeline: Define preferred_recovery_type e cost_to_airline, direcionando o Agente para ações de alta satisfação com menor queima de margem.
  4. Pergunta 4 — Fricção Logística Terrestre vs. Conforto do Aeroporto:
      • Foco no Passageiro: Critério de decisão entre voar por grandes hubs (Viracopos, Guarulhos, Confins) versus aeroportos centrais de fácil acesso urbano (Congonhas, Santos Dumont).
      • Alimentação no Pipeline: Alimenta hub_affinity_score e ground_friction_penalty, identificando quando o Agente deve prescrever parcerias de mobilidade (transfers,
      estacionamentos) para defender a rota.
  5. Pergunta 5 — Defesa contra Status Match e Risco de Rebaixamento de Categoria:
      • Foco no Passageiro: Comportamento no 2º semestre ao notar que não baterá a meta de renovação de status (se voa mais, se aceita rebaixamento, se aceita Status Match de
      concorrente ou se é indiferente).
      • Alimentação no Pipeline: Alimenta status_match_propensity e tier_defense_loyalty, disparando o gatilho de desafios de requalificação rápida (Fast-Track).
  6. Pergunta 6 — Razão de Pesquisas de Passagens Não Concluídas (Demanda Sombra):
      • Foco no Passageiro: Motivo principal da desistência após busca em app/site (horário incompatível com agenda, teto da política de viagens corporativas, falta de assentos premium
      ou apenas simulação casual).
      • Alimentação no Pipeline: Mapeia abandon_primary_cause e schedule_friction_weight, separando navegações casuais de demandas corporativas reprimidas.
  7. Pergunta 7 — Inovação Decisiva para Fidelidade Exclusiva:
      • Foco no Passageiro: O diferencial definitivo que faria o passageiro concentrar todas as viagens em uma só empresa (resolução digital sem filas, benefícios estendidos à família,
      mobilidade de ponta a ponta ou garantia de status protegido).
      • Alimentação no Pipeline: Define o primary_retention_driver, direcionando o arquétipo mestre do Agente e os guardrails de recomendação.

  ──────
  ### Tabela de Mapeamento Técnico para a Base de Dados

            Pergunta          | Métrica / Feature            | Tipo                      |            Intervalo             | Uso pelo Agente / Pipeline
  ----------------------------|------------------------------|---------------------------|----------------------------------|------------------------------------------------------------
               P1             | bleisure_stay_rate           | Float                     |           0.00 a 1.00            | Estimativa de receita agregada familiar
               P2             | friction_sensitivity_weight  | Float                     |           0.00 a 1.00            | Ponderação de atrito operacional na probabilidade de churn
               P3             | preferred_recovery_type      | Categórico                |  Points, Upgrade, Voucher, Care  | Catálogo prescritivo da Próxima Melhor Ação (NBA)
               P4             | airport_proximity_risk_index | Float                     |           0.00 a 1.00            | Ativação de parcerias de mobilidade porta a porta
               P5             | status_match_vulnerability   | Float                     |           0.00 a 1.00            | Emissão preventiva de desafios de manutenção de status
               P6             | abandon_primary_cause        | Categórico                | Schedule, Price, Comfort, Casual | Alerta de rotas alternativas e liberação de assentos
               P7             | primary_retention_driver     | Categórico                |           4 Arquétipos           | Seleção do prompt do Agente e limites de custo

  O documento completo com as opções de resposta, pontuações e regras de negócio está atualizado e pronto para consulta em pesquisa_clientes_kpis.md.
