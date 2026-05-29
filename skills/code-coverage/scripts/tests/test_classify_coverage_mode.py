import classify_coverage_mode as ccm


def test_branch_heavy_forces_branch_priority():
    assert ccm.classify(branch_operator_count=30, current_line=10, current_branch=10,
                         target_line=70, target_branch=60) == "branch-priority"


def test_line_done_branch_far():
    # line quasi al target (60 >= 70*0.85=59.5), branch lontana (40 < 60*0.8=48)
    assert ccm.classify(branch_operator_count=5, current_line=60, current_branch=40,
                        target_line=70, target_branch=60) == "branch-priority"


def test_default_line_priority():
    assert ccm.classify(branch_operator_count=0, current_line=10, current_branch=10,
                        target_line=70, target_branch=60) == "line-priority"
