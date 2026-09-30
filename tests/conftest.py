"""Tests own their mock workers even though production Web shutdown detaches."""

import asyncio
import pytest


@pytest.fixture(autouse=True)
def close_test_runtimes(monkeypatch, tmp_path_factory):
    from hearth.core.lifecycle import ApplicationContext

    contexts = []
    original = ApplicationContext.__init__

    def track(self, *args, **kwargs):
        original(self, *args, **kwargs)
        contexts.append(self)

    monkeypatch.setattr(ApplicationContext, "__init__", track)
    yield
    root = tmp_path_factory.getbasetemp().resolve()
    for context in contexts:
        if (
            context.settings.reticulum.backend == "mock_process"
            and context.settings.data_dir.resolve().is_relative_to(root)
        ):
            asyncio.run(context.adapter.stop())
        context.database.dispose()
