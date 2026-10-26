# src/

Código reutilizável do projeto.

Estrutura sugerida para os próximos incrementos:

- `data/`: leitura, validação e transformação dos dados;
- `features/`: criação de atributos e scores;
- `models/`: CLV, churn e segmentação;
- `agent/`: recomendações, políticas e fallback;
- `policies/`: elegibilidade, aprovação humana e limites;
- `evaluation/`: métricas e avaliações.

O pipeline oficial vive em `src/` (executar com `python -m src.pipeline`); o MVP antigo (`pipeline.py`/`app.py` Streamlit) esta em `../legacy/` apenas por historico. A migracao para modulos em `src/` deve ser revisada pelo time.
