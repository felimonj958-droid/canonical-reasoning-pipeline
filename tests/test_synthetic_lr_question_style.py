from src.generate.content_quality_checks import check_question_style


def test_check_question_style_accepts_vulnerable_to_criticism_stem():
    stem = "The reasoning in the argument is most vulnerable to criticism on the grounds that it"
    flags = check_question_style(stem)
    assert flags == []


def test_check_question_style_accepts_flaw_describes_stem():
    stem = "Which one of the following most accurately describes a flaw in the argument?"
    flags = check_question_style(stem)
    assert flags == []


def test_check_question_style_flags_non_lsat_stem():
    stem = "How do you feel about this argument?"
    flags = check_question_style(stem)
    assert flags == ["question_not_lsat_style"]
