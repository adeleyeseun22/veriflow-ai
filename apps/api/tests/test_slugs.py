from veriflow_api.utils.slugs import slugify


def test_slugify_normalizes_human_names() -> None:
    assert slugify("  Evidence & Decision Intelligence  ") == "evidence-decision-intelligence"


def test_slugify_handles_unicode_and_empty_values() -> None:
    assert slugify("Café Résumé") == "cafe-resume"
    assert slugify("---") == "workspace"
