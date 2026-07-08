"""YAML <-> SemanticLayerSpec for the editor. Round-trip stable."""
from __future__ import annotations

import yaml

from app.core.errors import ValidationError
from app.schemas.semantic_layer import SemanticLayerSpec


def spec_to_yaml(spec: SemanticLayerSpec) -> str:
    data = spec.model_dump(exclude_none=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def yaml_to_spec(text: str) -> SemanticLayerSpec:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError("Semantic layer YAML must be a mapping at the top level")
    try:
        return SemanticLayerSpec.model_validate(data)
    except Exception as exc:  # pydantic ValidationError -> user-facing 422
        raise ValidationError(f"Semantic layer failed validation: {exc}") from exc
