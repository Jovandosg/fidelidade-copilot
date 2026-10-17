import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from pipeline import build

def test_build_contract():
    df = build(120)
    assert len(df) == 120
    assert df.high_value_score.between(0, 100).all()
    assert df.churn_risk.between(0, 1).all()
    assert df.segment.nunique() == 4
    assert (df.priority == "P1 - agir agora").sum() > 0
    assert df.customer_id.is_unique
