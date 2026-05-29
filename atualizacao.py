"""Verificação de atualização via version.json no GitHub (raw)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Literal
from tkinter import messagebox, ttk

import tkinter as tk

# URL do version.json na branch principal do repositório (ajuste usuário/repositório).
VERSION_JSON_URL = (
    "https://raw.githubusercontent.com/leosans-eng/gerador-relatorios-fotograficos/main/version.json"
)
REQUEST_TIMEOUT_SEC = 15
CHUNK_SIZE = 256 * 1024


def parse_version(value: str) -> tuple[int, ...]:
    text = str(value).strip().lstrip("vV")
    parts: list[int] = []
    for segment in text.split("."):
        segment = segment.split("-")[0].split("+")[0]
        if not segment:
            continue
        if not segment.isdigit():
            break
        parts.append(int(segment))
    return tuple(parts) if parts else (0,)


def is_remote_newer(remote_version: str, local_version: str) -> bool:
    return parse_version(remote_version) > parse_version(local_version)


def fetch_remote_version_info(
    app_version: str,
    url: str = VERSION_JSON_URL,
    timeout: int = REQUEST_TIMEOUT_SEC,
) -> dict | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"GeradorRelatoriosFotograficos/{app_version}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return None
    version = str(payload.get("version", "")).strip()
    download = str(payload.get("download", "")).strip()
    if not version or not download:
        return None
    return {
        "version": version,
        "download": download,
    }


def default_download_path() -> Path:
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads
    return Path(tempfile.gettempdir())


def download_file(
    url: str,
    destination: Path,
    app_version: str,
    *,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"GeradorRelatoriosFotograficos/{app_version}"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SEC) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if on_progress:
                    on_progress(downloaded, total)


class UpdateDialog(tk.Toplevel):
    def __init__(self, root: tk.Tk, info: dict, app_version: str):
        super().__init__(root)
        self.root = root
        self.info = info
        self.app_version = app_version
        self.download_path: Path | None = None
        self._cancelled = False

        remote_version = info["version"]
        self.title("Atualização disponível")
        self.resizable(False, False)
        self.transient(root)
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=f"Nova versão: {remote_version}",
            font=("", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text=f"Versão instalada: {app_version}",
        ).pack(anchor="w", pady=(4, 12))

        self.status_var = tk.StringVar(value="Preparando download do instalador...")
        ttk.Label(frame, textvariable=self.status_var, wraplength=420).pack(anchor="w", pady=(0, 6))

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=420)
        self.progress.pack(fill="x", pady=(0, 12))
        self.progress.start(12)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        self.install_button = ttk.Button(
            buttons,
            text="Instalar agora",
            command=self.install_download,
            state="disabled",
        )
        self.install_button.pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Abrir pasta", command=self.open_download_folder).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Depois", command=self.close_dialog).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self.close_dialog)
        self.update_idletasks()
        self._center_on_parent(root)

        self.after(200, self.start_download)

    def _center_on_parent(self, parent: tk.Tk) -> None:
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        width = self.winfo_width()
        height = self.winfo_height()
        x = px + max(0, (pw - width) // 2)
        y = py + max(0, (ph - height) // 2)
        self.geometry(f"+{x}+{y}")

    def close_dialog(self) -> None:
        self._cancelled = True
        self.grab_release()
        self.destroy()

    def start_download(self) -> None:
        thread = threading.Thread(target=self._download_worker, daemon=True)
        thread.start()

    def _download_worker(self) -> None:
        destination = default_download_path()
        try:

            def on_progress(done: int, total: int) -> None:
                if self._cancelled:
                    return
                if total > 0:
                    percent = min(100, int(done * 100 / total))
                    text = f"Baixando instalador... {percent}%"
                    mode = "determinate"
                    value = percent
                else:
                    text = "Baixando instalador..."
                    mode = "indeterminate"
                    value = 0
                self.root.after(0, lambda: self._update_progress(text, mode, value))

            download_file(
                self.info["download"],
                destination,
                self.app_version,
                on_progress=on_progress,
            )
            if self._cancelled:
                return
            self.download_path = destination
            self.root.after(0, self._on_download_success)
        except Exception as exc:
            if not self._cancelled:
                self.root.after(0, lambda: self._on_download_error(exc))

    def _update_progress(self, text: str, mode: Literal["determinate", "indeterminate"], value: int) -> None:
        if not self.winfo_exists():
            return
        self.status_var.set(text)
        self.progress.stop()
        self.progress.configure(mode=mode, maximum=100)
        if mode == "determinate":
            self.progress["value"] = value
        else:
            self.progress.start(12)

    def _on_download_success(self) -> None:
        if not self.winfo_exists():
            return
        self.progress.stop()
        self.progress.configure(mode="determinate", value=100)
        path = self.download_path
        self.status_var.set(f"Download concluído:\n{path}")
        self.install_button.configure(state="normal")
        messagebox.showinfo(
            "Atualização baixada",
            "O instalador foi baixado.\n\n"
            "Feche o programa e clique em \"Instalar agora\" para atualizar.",
            parent=self,
        )

    def _on_download_error(self, exc: Exception) -> None:
        if not self.winfo_exists():
            return
        self.progress.stop()
        self.status_var.set(f"Falha no download: {exc}")
        messagebox.showerror(
            "Erro no download",
            f"Não foi possível baixar a atualização.\n\n{exc}",
            parent=self,
        )

    def install_download(self) -> None:
        if not self.download_path or not self.download_path.exists():
            messagebox.showwarning("Aviso", "Arquivo do instalador não encontrado.", parent=self)
            return
        try:
            os.startfile(self.download_path)  # type: ignore[attr-defined]
        except AttributeError:
            subprocess.Popen([str(self.download_path)], shell=True)
        except OSError as exc:
            messagebox.showerror("Erro", f"Não foi possível abrir o instalador:\n{exc}", parent=self)
            return
        self.close_dialog()
        messagebox.showinfo(
            "Instalação",
            "O instalador foi aberto. Feche este programa antes de concluir a instalação.",
            parent=self.root,
        )

    def open_download_folder(self) -> None:
        if not self.download_path:
            return
        folder = self.download_path.parent
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
        except AttributeError:
            subprocess.Popen(["xdg-open", str(folder)])


def check_for_updates(root: tk.Tk, app_version: str, *, url: str = VERSION_JSON_URL) -> None:
    if os.environ.get("SKIP_UPDATE_CHECK", "").strip() in ("1", "true", "yes"):
        return

    def worker() -> None:
        try:
            info = fetch_remote_version_info(app_version, url)
            if info and is_remote_newer(info["version"], app_version):
                root.after(0, lambda: UpdateDialog(root, info, app_version))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
            pass

    threading.Thread(target=worker, daemon=True).start()


def iniciar_verificacao_atualizacao(root: tk.Tk, app_version: str) -> None:
    """Agenda verificação de atualização após a interface abrir."""
    root.after(2000, lambda: check_for_updates(root, app_version))
