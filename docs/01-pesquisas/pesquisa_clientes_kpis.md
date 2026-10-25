# Diagnóstico Analítico e Instrumento de Pesquisa Multicompanhias: Alimentação de KPIs para o Agente de CRM

**Projeto:** `fidelidade-copilot` — Desafio 3: CRM Aéreo de Alto Valor  
**Aplicação:** Pesquisa de Mercado e Benchmark Multicompanhias (Azul, GOL, LATAM e setor aéreo geral)  
**Objetivo:** Coletar dados comportamentais e perceptivos diretamente de passageiros de qualquer operadora para alimentar e calibrar as variáveis analíticas da base em [data/](file:///C:/Users/Sertoriel/Documents/GitHub/fidelidade-copilot/data/) e a inteligência do Agente de CRM.

---

## PARTE 1: Síntese do Benchmark do Setor Aéreo Nacional

A análise cruzada das três principais operadoras do Brasil (Azul, GOL e LATAM) e da regulação da ANAC (Resolução 400) evidencia que os passageiros corporativos e frequentes distribuem suas viagens por conveniência de malha e pontualidade, mas apresentam padrões comuns de atrito:

1. **Multi-fidelização:** A maioria dos executivos mantém contas ativas em mais de um programa (Azul Fidelidade, Smiles da GOL e LATAM Pass), migrando o fluxo conforme a rota e a proximidade do aeroporto.
2. **Sensibilidade à Fricção Logística:** A preferência entre aeroportos centrais (Congonhas/CGH, Santos Dumont/SDU) e grandes hubs ou aeroportos metropolitanos (Viracopos/VCP, Guarulhos/GRU, Confins/CNF) é altamente mediada pelo tempo de trânsito rodoviário e pela facilidade de conexões rápidas.
3. **Migração Silenciosa:** O passageiro raramente formaliza queixa por atrasos médios; ele simplesmente transfere as compras seguintes para a companhia concorrente da mesma rota caso a experiência pós-atrito seja frustrante.

---

## PARTE 2: As 7 Perguntas Multicompanhias para Clientes Finais (Survey de Mercado)

As perguntas abaixo foram neutralizadas para aplicação com clientes de **qualquer companhia aérea** comercial (Azul, LATAM, GOL, internacionais). Cada alternativa gera valores padronizados que alimentam o pipeline analítico do Agente.

---

### Pergunta 1: Extensão de Viagens Corporativas e Viagens em Família (Sinergia Bleisure)
> *"Pensando na sua rotina de viagens no último ano, com que frequência você aproveitou viagens de negócios para esticar o fim de semana no destino ou costuma viajar a lazer com seus familiares?"*

- **A)** Praticamente nunca viajo a lazer ou levo acompanhantes; minhas viagens de avião são 100% corporativas individuais.  
  *(Alimenta: `bleisure_stay_rate` = 0.00 | `family_pnr_share` = 0.00 | `leisure_segment` = "Exclusivo Corporativo")*
- **B)** Raramente (1 a 2 vezes ao ano em férias pontuais com a família, geralmente escolhendo a passagem mais barata independente da companhia).  
  *(Alimenta: `bleisure_stay_rate` = 0.10 | `family_pnr_share` = 0.15 | `leisure_segment` = "Ocasional Preço-Sensível")*
- **C)** Com frequência moderada (estendo o fim de semana em 3 a 5 viagens de trabalho por ano e viajo em feriados com a família, preferindo a companhia onde tenho benefícios).  
  *(Alimenta: `bleisure_stay_rate` = 0.35 | `family_pnr_share` = 0.45 | `leisure_segment` = "Bleisure Ativo")*
- **D)** Muito frequente (sempre que possível incluo cônjuge/filhos nas minhas viagens profissionais e concentro todas as férias familiares na minha companhia aérea principal).  
  *(Alimenta: `bleisure_stay_rate` = 0.65 | `family_pnr_share` = 0.80 | `leisure_segment` = "VIP Bleisure Familiar")*

> **Finalidade para o Agente:** Estimar o potencial de conversão de bilhetes de múltiplos passageiros (B2C de alta rentabilidade) a partir de um cliente identificado inicialmente apenas pelo perfil corporativo B2B.

---

### Pergunta 2: Impacto de Imprevistos Operacionais na Lealdade (Fricção e Churn Silencioso)
> *"Caso seu voo sofra um atraso relevante (acima de 60 minutos) ou uma perda de conexão, qual costuma ser a sua atitude em relação aos seus próximos voos naquela mesma rota?"*

- **A)** Compreendo a complexidade do setor aéreo e isso não altera em nada minha escolha pela mesma companhia nos voos seguintes.  
  *(Alimenta: `friction_sensitivity_weight` = 0.15 | `silent_churn_risk` = 0.05)*
- **B)** Fico insatisfeito no momento, mas continuo voando na mesma empresa se o atendimento prestar as assistências obrigatórias adequadamente.  
  *(Alimenta: `friction_sensitivity_weight` = 0.40 | `silent_churn_risk` = 0.20)*
- **C)** Fico bastante incomodado e, nas semanas seguintes, passo a priorizar voos de companhias concorrentes que operem rotas e horários semelhantes.  
  *(Alimenta: `friction_sensitivity_weight` = 0.80 | `silent_churn_risk` = 0.65)*
- **D)** Deixo de voar imediatamente com a empresa responsável pelo atraso e transfiro todo o meu volume de viagens para a concorrência sem abrir chamado de reclamação.  
  *(Alimenta: `friction_sensitivity_weight` = 1.00 | `silent_churn_risk` = 0.95 [Alerta Crítico P1])*

> **Finalidade para o Agente:** Calibrar o peso do índice de atrito acumulado (`weighted_friction_index`) para disparar intervenções de retenção antes que o cliente pare de voar.

---

### Pergunta 3: Modelo Ideal de Recuperação de Confiança (Recovery Proativo)
> *"Quando ocorre uma falha ou atraso no seu voo, qual atitude proativa por parte da companhia aérea demonstra o maior respeito pelo seu valor como cliente?"*

- **A)** Crédito automático de milhas ou pontos qualificáveis no programa de fidelidade para me ajudar a subir ou manter minha categoria.  
  *(Alimenta: `preferred_recovery_type` = "Qualifying Points" | `cost_to_airline` = "Baixo")*
- **B)** Cortesia imediata de upgrade para assento com maior espaço para pernas ou acesso à Sala VIP no próximo voo.  
  *(Alimenta: `preferred_recovery_type` = "Seat/Lounge Upgrade" | `cost_to_airline` = "Médio")*
- **C)** Um voucher de desconto em dinheiro para dedução direta no valor da próxima compra de passagem.  
  *(Alimenta: `preferred_recovery_type` = "Cash Fare Voucher" | `cost_to_airline` = "Alto")*
- **D)** Um contato dedicado e transparente (via aplicativo ou consultor exclusivo) informando as providências tomadas para minimizar meu transtorno.  
  *(Alimenta: `preferred_recovery_type` = "Concierge Communication" | `cost_to_airline` = "Baixo")*

> **Finalidade para o Agente:** Recomendar a melhor próxima ação (NBA) que maximize a percepção de valor e satisfação do passageiro mantendo o custo da compensação compatível com a margem econômica (`estimated_margin`).

---

### Pergunta 4: Fricção Logística Terrestre vs. Conforto do Aeroporto (Jornada Porta a Porta)
> *"Ao escolher entre um voo partindo de um grande hub aeroportuário (como Viracopos, Guarulhos ou Confins) e um voo saindo de um aeroporto central de fácil acesso urbano (como Congonhas ou Santos Dumont), qual critério é decisivo para você?"*

- **A)** Prefiro o grande hub pelo conforto das aeronaves, menor índice de congestionamento aéreo e pontualidade geral, mesmo que o trajeto terrestre seja mais longo.  
  *(Alimenta: `hub_affinity_score` = 1.00 | `ground_friction_penalty` = 0.10)*
- **B)** Escolho voar pelo grande hub com frequência, desde que a companhia aérea disponibilize facilidades como ônibus executivo dedicado ou parcerias de estacionamento.  
  *(Alimenta: `hub_affinity_score` = 0.70 | `ground_friction_penalty` = 0.35)*
- **C)** Só escolho o grande hub quando a diferença de preço da passagem for muito atrativa ou não existirem voos diretos no aeroporto central da cidade.  
  *(Alimenta: `hub_affinity_score` = 0.30 | `ground_friction_penalty` = 0.70)*
- **D)** Evito grandes hubs sempre que possível para fugir do trânsito nas rodovias; opto quase que exclusivamente por aeroportos centrais (Congonhas/Santos Dumont).  
  *(Alimenta: `hub_affinity_score` = 0.05 | `ground_friction_penalty` = 0.95)*

> **Finalidade para o Agente:** Identificar se o cliente sofre risco de evasão por conveniência geográfica (`airport_proximity_risk_index`), recomendando benefícios de mobilidade terrestre (transfers, estacionamentos, parcerias locais) para proteger rotas originadas em hubs.

---

### Pergunta 5: Comportamento Diante da Manutenção de Nível de Fidelidade (Status Match Defense)
> *"Se no segundo semestre do ano você perceber que não atingirá o total de voos ou pontos necessários para renovar seu status superior em uma companhia aérea (como Diamante, Black ou Platinum), o que você costuma fazer?"*

- **A)** Concentro intencionalmente mais viagens naquela companhia para não perder meu nível e benefícios conquistados.  
  *(Alimenta: `tier_defense_loyalty` = 1.00 | `status_match_propensity` = 0.05)*
- **B)** Aceito o rebaixamento de categoria com naturalidade e sigo comprando apenas pelas rotas e horários que melhor atendem à minha agenda.  
  *(Alimenta: `tier_defense_loyalty` = 0.50 | `status_match_propensity` = 0.35)*
- **C)** Se um programa concorrente me oferecer equiparação de categoria (Status Match ou desafio rápido), transfiro imediatamente meus voos para lá.  
  *(Alimenta: `tier_defense_loyalty` = 0.15 | `status_match_propensity` = 0.85)*
- **D)** Não acompanho ativamente regras de qualificação de programas; minha decisão é 100% orientada por horário, preço corporativo e conveniência do voo.  
  *(Alimenta: `tier_defense_loyalty` = 0.00 | `status_match_propensity` = 0.50)*

> **Finalidade para o Agente:** Avaliar a vulnerabilidade competitiva do cliente (`status_match_vulnerability_score`) no 3º trimestre do ano civil, orientando a emissão de desafios rápidos de requalificação (Fast-Tracks).

---

### Pergunta 6: Razão Primária de Pesquisas de Passagens Não Concluídas (Demanda Sombra)
> *"Ao pesquisar passagens em aplicativos ou sites de companhias aéreas para um compromisso e decidir não concluir a reserva, qual costuma ser o principal motivo da desistência?"*

- **A)** Incompatibilidade de horários: os voos disponíveis chegavam muito tarde ou partiam em horários conflitantes com minha agenda de trabalho.  
  *(Alimenta: `abandon_primary_cause` = "Schedule Mismatch" | `schedule_friction_weight` = 0.90)*
- **B)** Teto tarifário: o valor da passagem ultrapassava o limite da política de viagens corporativas da minha empresa ou o valor aceitável de mercado.  
  *(Alimenta: `abandon_primary_cause` = "Corporate Policy Limit" | `price_sensitivity_score` = 0.85)*
- **C)** Falta de conforto/disponibilidade: os melhores assentos da aeronave (primeiras fileiras ou espaço extra para pernas) já estavam todos ocupados.  
  *(Alimenta: `abandon_primary_cause` = "Seat Availability Failure" | `comfort_sensitivity_score` = 0.80)*
- **D)** Consulta exploratória: estava apenas simulando opções e preços sem ter uma data ou viagem realmente definida.  
  *(Alimenta: `abandon_primary_cause` = "Exploratory Window-Shopping" | `intent_strength_score` = 0.10)*

> **Finalidade para o Agente:** Distinguir abandono casual de demanda corporativa reprimida por horários ou políticas internas, acionando notificações inteligentes de flexibilização de rota ou liberação de assentos.

---

### Pergunta 7: Inovação Decisiva para Concentração de Voos (Fator de Fidelidade Exclusiva)
> *"Se as companhias aéreas pudessem implementar uma única melhoria no serviço, qual delas faria você concentrar praticamente todas as suas viagens em uma única empresa?"*

- **A)** Atendimento resolutivo e sem filas: um canal direto no aplicativo que altera passagens e resolve conexões perdidas em poucos toques, sem esperar call center.  
  *(Alimenta: `primary_retention_driver` = "Frictionless Digital Service" | `crm_archetype` = "Autonomia Digital")*
- **B)** Benefícios compartilhados: extensão automática dos meus privilégios de bagagem, assento conforto e embarque prioritário para os familiares que viajam comigo.  
  *(Alimenta: `primary_retention_driver` = "Family Shared Privileges" | `crm_archetype` = "Família e Bleisure")*
- **C)** Jornada integrada de ponta a ponta: parcerias que cuidam do transporte terrestre (transfer/estacionamento) e facilidades no destino (hotéis e locação de veículos).  
  *(Alimenta: `primary_retention_driver` = "Integrated Door-to-Door Mobility" | `crm_archetype` = "Mobilidade Integrada")*
- **D)** Garantia de status protegido: regras que não rebaixem bruscamente meu nível em anos com menor quantidade de viagens profissionais atípicas.  
  *(Alimenta: `primary_retention_driver` = "Tier Soft-Landing Assurance" | `crm_archetype` = "Proteção de Status")*

> **Finalidade para o Agente:** Atribuir o arquétipo mestre de personalização do cliente, garantindo que o Agente utilize os prompts e guardrails correspondentes para sugerir ações contextuais adequadas a cada perfil.

---

## Matriz de Mapeamento com a Base de Dados do Projeto (`data/analytics/customer_features`)

| Pergunta | Variável Analítica Gerada | Tipo de Dado | Intervalo de Valores | Impacto Direto no Agente |
|---|---|---|---|---|
| **P1** | `bleisure_stay_rate` | Float | `0.00` a `1.00` | Pondera potencial de receita familiar e ofertas de múltiplos assentos |
| **P2** | `friction_sensitivity_weight` | Float | `0.00` a `1.00` | Multiplica o impacto de atrasos registrados em `churn_risk` |
| **P3** | `preferred_recovery_type` | Categórico | `Points`, `Upgrade`, `Voucher`, `Care` | Seleciona o catálogo de ações da Próxima Melhor Ação (NBA) |
| **P4** | `airport_proximity_risk_index` | Float | `0.00` a `1.00` | Identifica fuga para aeroportos centrais concorrentes |
| **P5** | `status_match_vulnerability` | Float | `0.00` a `1.00` | Aciona gatilhos de desafios rápidos (Fast-Track) no 3º trimestre |
| **P6** | `abandon_primary_cause` | Categórico | `Schedule`, `Price`, `Comfort`, `Casual` | Filtra alarmes falsos de navegação e atua em demandas de agenda |
| **P7** | `primary_retention_driver` | Categórico | 4 Arquétipos | Define o tom do prompt do Agente e a política de guardrail de custo |

Com essa reformulação multiaérea, o formulário pode ser distribuído para passageiros frequentes de qualquer companhia ou operadora, gerando inteligência comparativa e calibrando com alta precisão o motor analítico e o Agente do sistema.
