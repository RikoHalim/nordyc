"""Offline schema compatibility checks; no provider requests."""

from copy import deepcopy

import pytest
from pydantic import TypeAdapter, ValidationError

from shiftos.schemas.analysis import CourseFindingResult, ProgrammeResult, ProgrammeSummary
from shiftos.services.analysis.providers import _claude_transport_schema


@pytest.mark.parametrize(
    ("model", "field", "invalid"),
    [
        (ProgrammeResult, "schema_version", "invalid-version"),
        (CourseFindingResult, "is_final_curriculum_verdict", True),
        (ProgrammeSummary, "notice", "Definitive curriculum verdict"),
    ],
)
def test_transport_literals_use_singleton_enums_without_weakening_validation(model, field, invalid):
    original = model.model_json_schema()
    before = deepcopy(original)
    transport = _claude_transport_schema(original)
    literal = original["properties"][field]["const"]
    assert transport["properties"][field]["enum"] == [literal]
    assert "const" not in transport["properties"][field]
    assert original == before
    adapter = TypeAdapter(model.model_fields[field].annotation)
    assert adapter.validate_python(literal) == literal
    with pytest.raises(ValidationError):
        adapter.validate_python(invalid)


def test_large_choice_grammar_is_described_but_original_validation_remains_strict():
    original = ProgrammeResult.model_json_schema()
    before = deepcopy(original)
    transport = _claude_transport_schema(original)
    allowed = original["properties"]["result_mode"]["enum"]
    field = transport["properties"]["result_mode"]
    assert "enum" not in field
    assert all(value in field["description"] for value in allowed)
    assert original == before
    adapter = TypeAdapter(ProgrammeResult.model_fields["result_mode"].annotation)
    for value in allowed:
        assert adapter.validate_python(value) == value
    with pytest.raises(ValidationError):
        adapter.validate_python("fabricated_result")
