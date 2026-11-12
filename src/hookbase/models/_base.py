from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

#: `model_config` for a model that carries a secret or credential; pydantic merges it over
#: HookbaseModel's. A validation error then leaves out its input, which pydantic otherwise prints
#: truncated and whose tail can be the secret; `_pagination._parse_list` does the same for a list
#: of one. Give the secret field `Field(repr=False)` too, for repr() and str().
SECRET_MODEL_CONFIG = ConfigDict(hide_input_in_errors=True)


class HookbaseModel(BaseModel):
    """Base model with camelCase alias support for API compatibility."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )
