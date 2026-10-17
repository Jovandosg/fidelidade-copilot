# src/

Código reutilizável do projeto.

Estrutura sugerida para os próximos incrementos:

- `data/`: leitura, validação e transformação dos dados;
- `features/`: criação de atributos e scores;
- `models/`: CLV, churn e segmentação;
- `agent/`: recomendações, políticas e fallback;
- `policies/`: elegibilidade, aprovação humana e limites;
- `evaluation/`: métricas e avaliações.

A implementação inicial do MVP permanece em `pipeline.py` e `app.py` para reduzir a complexidade do primeiro Sprint. A migração para módulos em `src/` deve acontecer somente quando gerar valor e for revisada pelo time.
