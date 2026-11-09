from __future__ import annotations

import dataclasses
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from aurora.api import create_app
from aurora.config import get_settings, Settings
from aurora.service import AuroraService

from .fake_llm import FakeLlm


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return dataclasses.replace(
        get_settings(),
        db_path=tmp_path / "condominio.db",
        sessions_db_path=tmp_path / "sessoes.db",
    )


def make_service(settings: Settings, malicioso: bool = False) -> AuroraService:
    return AuroraService(
        settings,
        modelo_principal=FakeLlm(malicioso=malicioso),
        modelo_especialistas=FakeLlm(malicioso=malicioso),
    )


@pytest.fixture
def abrir_api(settings: Settings):
    """Sobe a API (lifespan completo). Chamar de novo = reiniciar a API."""

    @contextmanager
    def _abrir(malicioso: bool = False) -> Iterator[TestClient]:
        app = create_app(lambda: make_service(settings, malicioso))
        with TestClient(app) as client:
            yield client

    return _abrir


@pytest.fixture
def api(abrir_api) -> Iterator[TestClient]:
    with abrir_api() as client:
        yield client
