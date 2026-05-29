"""Caminhos do app em desenvolvimento e no executável PyInstaller."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Pasta do programa — dados do usuário (JSON, imagens) ficam aqui."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """Recursos empacotados (modelos, ícone, anomalias padrão)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent


def icon_path() -> Path | None:
    for candidate in (
        bundle_dir() / "setup" / "icone.ico",
        app_dir() / "setup" / "icone.ico",
    ):
        if candidate.is_file():
            return candidate
    return None
