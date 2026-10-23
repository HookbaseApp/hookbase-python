"""Every public model, alias and constant in hookbase.models.* is exported from hookbase.models."""

from __future__ import annotations

import importlib
import pkgutil

import hookbase.models as models


def _public_definitions(module):
    """Classes defined in the module, plus its top-level aliases and constants."""
    with open(module.__file__) as fh:
        source = fh.read()
    for name, obj in list(vars(module).items()):
        if name.startswith("_") or name[0].islower():
            continue
        defined_here = getattr(obj, "__module__", None) == module.__name__
        if defined_here or f"\n{name} = " in source or f"\n{name}: " in source:
            yield name


def test_all_model_names_are_exported():
    missing = []
    for info in pkgutil.iter_modules(models.__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"hookbase.models.{info.name}")
        for name in _public_definitions(module):
            if name not in models.__all__ or not hasattr(models, name):
                missing.append(f"{info.name}.{name}")
    assert missing == []


def test_portal_token_params_exported():
    from hookbase.models import CreatePortalTokenParams, PortalToken

    assert CreatePortalTokenParams.__name__ == "CreatePortalTokenParams"
    assert PortalToken.__name__ == "PortalToken"


def test_all_entries_resolve():
    for name in models.__all__:
        assert hasattr(models, name), name
