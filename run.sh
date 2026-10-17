#!/usr/bin/env bash
set -euo pipefail
python pipeline.py
streamlit run app.py
