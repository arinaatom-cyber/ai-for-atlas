"""LLM summary sanitization — Russian gloss fixes."""

from atlas_agent.discovery.evaluation.sanitize import fix_ru_llm_gloss, sanitize_summary


def test_fix_paysage_gloss():
    raw = "Этот пейсаж не полностью соответствует атласу."
    assert "абстракт" in fix_ru_llm_gloss(raw)
    assert "пейсаж" not in fix_ru_llm_gloss(raw)


def test_fix_pejdzh_gloss():
    raw = "Этот пейдж не полностью соответствует атласу."
    fixed = fix_ru_llm_gloss(raw)
    assert "статья" in fixed
    assert "пейдж" not in fixed


def test_fix_ffpe_misread():
    raw = (
        "Этот пейсаж не полностью соответствует атласу, так как он сосредоточен на анализе FFPE образцов, "
        "что не включает в себя ткань или клетки опухоли."
    )
    fixed = sanitize_summary(raw)
    assert "FFPE ткани опухоли допустимы" in fixed


def test_fix_paket_dannyh():
    raw = "Этот пакет данных соответствует атласу по протеомике TMT."
    assert "пакет данных" not in sanitize_summary(raw)
