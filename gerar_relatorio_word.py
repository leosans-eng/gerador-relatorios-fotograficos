"""Gera relatório fotográfico em Word a partir do modelo padrão."""

from __future__ import annotations

import os
import re
import shutil
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox

from docx import Document
from docx.shared import Emu
from docx.table import Table

_W_PPR_LOCAL_TAG = "pPr"

APP_DIR = Path(__file__).resolve().parent
PHOTOS_PER_TABLE = 12
TABLE_ROWS = 6
TABLE_COLS = 2
IMAGE_WIDTH = Emu(2667000)
IMAGE_HEIGHT = Emu(1917700)

TEMPLATE_CANDIDATES = [
    APP_DIR / "modelos" / "relatorio_modelo.docx",
    Path.home() / "Downloads" / "2. RELATÓRIO FOTOGRÁFICO-ÁREA COMUM-COND. XXXXXXXXXXXX-CIDADE-UF.docx",
]


def resolve_template_path() -> Path:
    for candidate in TEMPLATE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Modelo Word não encontrado. Coloque o arquivo em 'modelos/relatorio_modelo.docx' "
        "ou em Downloads com o nome padrão do relatório."
    )


def sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", value.strip())
    return cleaned or "SEM-NOME"


def default_output_name(condominio_name: str) -> str:
    condo = sanitize_filename_part(condominio_name).upper()
    return f"2. RELATÓRIO FOTOGRÁFICO-ÁREA COMUM-COND. {condo}-CIDADE-UF.docx"


def default_downloads_dir() -> Path:
    downloads = Path.home() / "Downloads"
    return downloads if downloads.exists() else Path.home()


def photos_without_anomaly(condominio_data: dict) -> list[tuple[str, int, str]]:
    missing = []
    for section in condominio_data.get("sections", []):
        section_name = section.get("name", "Sem nome")
        for photo in section.get("photos", []):
            if not str(photo.get("anomaly", "")).strip():
                missing.append(
                    (
                        section_name,
                        int(photo.get("order", 0)),
                        os.path.basename(str(photo.get("path", ""))),
                    )
                )
    return missing


def resolve_image_path(path_str: str) -> Path | None:
    if not path_str:
        return None
    path = Path(path_str)
    if path.is_file():
        return path
    relative = APP_DIR / path
    if relative.is_file():
        return relative
    return None


def _clear_paragraph(paragraph):
    element = paragraph._element
    for child in list(element):
        if child.tag.split("}")[-1] != _W_PPR_LOCAL_TAG:
            element.remove(child)


def _set_caption(paragraph, photo_number: int, anomaly: str):
    _clear_paragraph(paragraph)
    text = f"Foto {photo_number} – {anomaly}"
    paragraph.add_run(text)


def _set_image(paragraph, image_path: Path):
    _clear_paragraph(paragraph)
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=IMAGE_WIDTH, height=IMAGE_HEIGHT)


def _clear_photo_cell(cell):
    if len(cell.paragraphs) >= 1:
        _clear_paragraph(cell.paragraphs[0])
    if len(cell.paragraphs) >= 2:
        _clear_paragraph(cell.paragraphs[1])


def _fill_photo_cell(cell, image_path: Path, photo_number: int, anomaly: str):
    if len(cell.paragraphs) < 2:
        raise ValueError("Célula do modelo não possui estrutura esperada (imagem + legenda).")
    _set_image(cell.paragraphs[0], image_path)
    _set_caption(cell.paragraphs[1], photo_number, anomaly)


def _populate_table(table, photos: list[dict], start_photo_number: int):
    for index in range(PHOTOS_PER_TABLE):
        row = index // TABLE_COLS
        col = index % TABLE_COLS
        cell = table.cell(row, col)
        if index < len(photos):
            photo = photos[index]
            image_path = resolve_image_path(str(photo.get("path", "")))
            if image_path is None:
                raise FileNotFoundError(
                    f"Imagem não encontrada para a foto {photo.get('order', '?')}: {photo.get('path', '')}"
                )
            _fill_photo_cell(
                cell,
                image_path,
                int(photo.get("order", start_photo_number + index)),
                str(photo.get("anomaly", "")).strip(),
            )
        else:
            _clear_photo_cell(cell)


def _remove_generated_content(doc):
    body = doc.element.body
    children = list(body)
    if len(children) < 2:
        return
    for child in children[2:-1]:
        body.remove(child)


def _insert_table_before_sectpr(doc, table_element):
    body = doc.element.body
    sect_pr = body[-1]
    body.insert(list(body).index(sect_pr), table_element)


def _add_heading(doc, text: str, style_name: str):
    paragraph = doc.add_paragraph(text, style=style_name)
    paragraph_element = paragraph._element
    body = doc.element.body
    sect_pr = body[-1]
    body.insert(list(body).index(sect_pr), paragraph_element)
    return paragraph


def _build_report_body(doc, condominio_data: dict):
    template_table = deepcopy(doc.tables[0]._tbl)
    _remove_generated_content(doc)
    _add_heading(doc, "REGISTROS FOTOGRÁFICOS ", "Heading 1")

    sections = condominio_data.get("sections", [])
    for section in sections:
        photos = sorted(section.get("photos", []), key=lambda item: item.get("order", 0))
        if not photos:
            continue
        _add_heading(doc, section.get("name", "Bloco"), "Heading 2")
        for chunk_start in range(0, len(photos), PHOTOS_PER_TABLE):
            chunk = photos[chunk_start : chunk_start + PHOTOS_PER_TABLE]
            new_table = deepcopy(template_table)
            _insert_table_before_sectpr(doc, new_table)
            table = Table(new_table, doc)
            start_number = int(chunk[0].get("order", chunk_start + 1)) if chunk else chunk_start + 1
            _populate_table(table, chunk, start_number)
            spacer = doc.add_paragraph("")
            spacer_element = spacer._element
            body = doc.element.body
            sect_pr = body[-1]
            body.insert(list(body).index(sect_pr), spacer_element)


def gerar_relatorio(
    condominio_name: str,
    condominio_data: dict,
    *,
    parent=None,
    output_path: Path | None = None,
    ask_save_path: bool = True,
    open_after_save: bool = True,
) -> Path:
    missing = photos_without_anomaly(condominio_data)
    if missing:
        raise ValueError("Existem fotos sem anomalia selecionada.")

    total_photos = sum(len(section.get("photos", [])) for section in condominio_data.get("sections", []))
    if total_photos == 0:
        raise ValueError("Não há fotos para gerar o relatório.")

    template_path = resolve_template_path()
    if output_path is None:
        suggested_name = default_output_name(condominio_name)
        initial_dir = default_downloads_dir()
        if ask_save_path:
            selected = filedialog.asksaveasfilename(
                parent=parent,
                title="Salvar relatório Word",
                defaultextension=".docx",
                filetypes=[("Documento Word", "*.docx")],
                initialdir=str(initial_dir),
                initialfile=suggested_name,
            )
            if not selected:
                raise RuntimeError("Salvamento cancelado pelo usuário.")
            output_path = Path(selected)
        else:
            output_path = initial_dir / suggested_name

    output_path = Path(output_path)
    if output_path.suffix.lower() != ".docx":
        output_path = output_path.with_suffix(".docx")

    shutil.copy2(template_path, output_path)
    doc = Document(str(output_path))
    _build_report_body(doc, condominio_data)
    doc.save(str(output_path))

    if open_after_save:
        os.startfile(str(output_path))

    return output_path


if __name__ == "__main__":
    import json
    import tkinter as tk

    data_file = APP_DIR / "condominios.json"
    if not data_file.exists():
        raise SystemExit("Arquivo condominios.json não encontrado.")

    with data_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    condominio_name = data.get("current_condominio") or ""
    if not condominio_name:
        raise SystemExit("Nenhum condomínio selecionado em condominios.json.")

    condominio_data = data["condominios"].get(condominio_name)
    if not condominio_data:
        raise SystemExit(f"Condomínio '{condominio_name}' não encontrado.")

    root = tk.Tk()
    root.withdraw()
    try:
        path = gerar_relatorio(condominio_name, condominio_data, parent=root)
        messagebox.showinfo("Relatório gerado", f"Arquivo salvo em:\n{path}", parent=root)
    except Exception as exc:
        messagebox.showerror("Erro ao gerar relatório", str(exc), parent=root)
    finally:
        root.destroy()
