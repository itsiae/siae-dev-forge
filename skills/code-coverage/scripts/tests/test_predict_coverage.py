import predict_coverage as pc


def test_predict_flags_branch_risk():
    out = pc.predict(size_class="VERY_LARGE", n_batches=3, total_loc=31000,
                     pre_line=59.08, pre_branch=42.31, target_line=70, target_branch=70)
    assert "predicted_branch_after_phase7" in out["predictions"]
    assert out["predictions"]["confidence"] in ("LOW", "MEDIUM")
    # branch target 70 alto + base 42 → rischio
    assert any(f["flag"] == "BRANCH_GAP_HIGH_RISK" for f in out["risk_flags"])


def test_no_risk_when_target_low():
    out = pc.predict(size_class="MEDIUM", n_batches=2, total_loc=8000,
                     pre_line=65, pre_branch=60, target_line=70, target_branch=60)
    assert out["risk_flags"] == [] or all(
        f["flag"] != "BRANCH_GAP_HIGH_RISK" for f in out["risk_flags"])


def test_confidence_low_without_branch_data():
    out = pc.predict(size_class="LARGE", n_batches=4, total_loc=20000,
                     pre_line=50, pre_branch=0, target_line=70, target_branch=60)
    assert out["predictions"]["confidence"] == "LOW"
