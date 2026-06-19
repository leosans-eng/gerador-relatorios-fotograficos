import json
import os
import shutil
import sys
import uuid
import time
from pathlib import Path
from typing import Callable, Protocol, cast
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageGrab, ImageTk

from app_paths import app_dir, icon_path

APP_VERSION = "1.0.6"
APP_ROOT = app_dir()
DATA_FILE = APP_ROOT / "condominios.json"
ANOMALY_FILE = APP_ROOT / "anomalias.json"
IMAGE_DIR = APP_ROOT / "imagens"
AUTOSAVE_MS = 5 * 60 * 1000
DEFAULT_ANOMALIAS = [
    "Armadura exposta",
    "Caixas de inspeção em desacordo à NBR 9050",
    "Cobertura de acesso ao bloco",
    "Concreção ferruginosa",
    "Condutor em desacordo à NBR 10844",
    "Contenção de talude",
    "Corrimão em desacordo à NBR 9050",
    "Corrosão de elementos metálicos",
    "Degraus em desacordo à NBR 9050",
    "Destacamento do revestimento",
    "Destelhamento",
    "Deterioração da pavimentação",
    "Deterioração do abrigo",
    "Deterioração do calçamento",
    "Drenagem superficial ineficiente",
    "Empolamento do revestimento",
    "Erosão do solo",
    "Faixa de umidade persistente",
    "Falha de aderência da pintura",
    "Falha na instalação do rufo",
    "Falha na junta de dilatação",
    "Falha na vedação/soldagem das conexões",
    "Falha na vinculação de elementos",
    "Falha no cobrimento da armadura",
    "Falta de calha de captação pluvial",
    "Falta de dispositivo DR",
    "Falta de piso tátil",
    "Falta de rufo pingadeira",
    "Falta de sinalização visual",
    "Falta ou falha da faixa de travessia",
    "Falta ou falha da rampa de acesso",
    "Falta ou falha da vaga acessível",
    "Falta ou falha de corrimão",
    "Falta ou falha do guarda-corpo",
    "Falta ou falha do peitoril",
    "Falta ou falha na impermeabilização da área molhada",
    "Fissura higroscópica",
    "Fissura mapeada",
    "Infiltração pela fachada",
    "Infiltração pelas esquadrias",
    "Infiltração pelo cobogó",
    "Má instalação das janelas",
    "Muro de arrimo com falta de drenagem",
    "Muro de arrimo com trincas e deformações",
    "Muro de divisa com trincas, deformação, umidade e reboco deteriorado",
    "Piso solto, trincado ou com som cavo",
    "Prolongamento insuficiente do peitoril",
    "Reboco em desacordo à NBR 13529",
    "Reboco em desacordo às NBRs 7200 e 13749",
    "Reparo inadequado",
    "Revestimento argamassado pulverulento",
    "Revestimento argamassado solto",
    "Rufo nas platibandas",
    "Tampas em desacordo à NBR 8160",
    "Transpasse inadequado do peitoril",
    "Trinca contígua à esquadria",
    "Trinca devido à deformação estrutural",
    "Trinca entre a laje e a alvenaria",
    "Trinca horizontal",
    "Trinca na laje do hall",
    "Trinca no abrigo",
    "Trinca no calçamento",
    "Trinca no calçamento perimetral",
    "Trinca saindo da janela",
    "Trinca saindo da porta",
    "Trinca vertical na alvenaria",
    "Umidade ascendente",
    "Umidade na laje",
    "Umidade na moldura",
    "Umidade no abrigo",
    "Umidade no alçapão",
    "Umidade pela fachada",
    "Utilização de elemento não estanque (cobogó)",
    "Vesículas no reboco da fachada",
]


class _TkinterDnDDropTarget(Protocol):
    """Métodos adicionados pelo tkdnd em widgets quando a janela usa TkinterDnD.Tk()."""

    def drop_target_register(self, format: object) -> str: ...

    def dnd_bind(
        self,
        sequence: str,
        func: Callable[..., object],
        /,
        *args: object,
    ) -> str: ...


class RelatorioFotograficoApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Gerador de Relatórios Fotográficos  v{APP_VERSION}")
        self.root.geometry("1240x760")
        self.root.minsize(1100, 700)
        self.root.state("zoomed")
        icon_file = icon_path()
        if icon_file:
            try:
                self.root.iconbitmap(str(icon_file))
            except tk.TclError:
                pass
        IMAGE_DIR.mkdir(exist_ok=True)
        self.data = {
            "condominios": {},
            "current_condominio": None,
        }
        self.current_cond = None
        self.current_section_index = 0
        self.preview_image = None
        self.anomalias = []
        self.collapsed_section_names = set()
        self._handling_tree_select = False
        self.last_action_var = tk.StringVar(value="Nenhuma ação registrada.")

        self.load_data()
        self.load_anomalias()
        self.build_ui()
        self.refresh_condominios()
        self.root.after(AUTOSAVE_MS, self.autosave)
        self.schedule_update_check()

    def load_data(self):
        if DATA_FILE.exists():
            try:
                with DATA_FILE.open("r", encoding="utf-8") as handle:
                    self.data = json.load(handle)
                self.data.setdefault("condominios", {})
                self.data.setdefault("current_condominio", None)
            except Exception:
                messagebox.showwarning(
                    "Aviso", "Não foi possível ler o arquivo de dados. Um novo arquivo será criado."
                )
                self.data = {"condominios": {}, "current_condominio": None}
        else:
            self.data = {"condominios": {}, "current_condominio": None}

    def save_data(self):
        try:
            with DATA_FILE.open("w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao salvar dados: {exc}")

    def autosave(self):
        self.save_data()
        self.root.after(AUTOSAVE_MS, self.autosave)

    def load_anomalias(self):
        if ANOMALY_FILE.exists():
            try:
                with ANOMALY_FILE.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    loaded = data.get("anomalias", [])
                else:
                    loaded = data
                if not isinstance(loaded, list):
                    loaded = []
                self.anomalias = [str(item).strip() for item in loaded if str(item).strip()]
            except Exception:
                self.anomalias = DEFAULT_ANOMALIAS.copy()
        else:
            self.anomalias = DEFAULT_ANOMALIAS.copy()
            self.save_anomalias()
        if not self.anomalias:
            self.anomalias = DEFAULT_ANOMALIAS.copy()
            self.save_anomalias()

    def save_anomalias(self):
        try:
            with ANOMALY_FILE.open("w", encoding="utf-8") as handle:
                json.dump({"anomalias": self.anomalias}, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao salvar anomalias: {exc}")

    def refresh_anomaly_combo(self):
        query = self.anomaly_var.get().strip()
        if query:
            self.filter_anomaly_combo()
        else:
            self.anomaly_combo["values"] = self.anomalias

    def filter_anomaly_combo(self):
        query = self.anomaly_var.get().strip().casefold()
        if not query:
            self.anomaly_combo["values"] = self.anomalias
            return
        filtered = [name for name in self.anomalias if query in name.casefold()]
        self.anomaly_combo["values"] = filtered

    def resolve_anomaly_name(self, text):
        text = text.strip()
        if not text:
            return None
        text_fold = text.casefold()
        for name in self.anomalias:
            if name.casefold() == text_fold:
                return name
        starts_with = [name for name in self.anomalias if name.casefold().startswith(text_fold)]
        if len(starts_with) == 1:
            return starts_with[0]
        contains = [name for name in self.anomalias if text_fold in name.casefold()]
        if len(contains) == 1:
            return contains[0]
        if starts_with:
            return starts_with[0]
        if contains:
            return contains[0]
        return None

    def set_last_action(self, message):
        self.last_action_var.set(message)

    def schedule_update_check(self):
        try:
            from atualizacao import iniciar_verificacao_atualizacao

            iniciar_verificacao_atualizacao(self.root, APP_VERSION)
        except ImportError:
            pass

    def build_ui(self):
        self.setup_styles()

        top_frame = ttk.Frame(self.root, padding=(10, 10, 10, 0))
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="Condomínio:").pack(side="left")
        self.condo_var = tk.StringVar()
        self.condo_combo = ttk.Combobox(
            top_frame,
            textvariable=self.condo_var,
            state="readonly",
            width=60,
        )
        self.condo_combo.pack(side="left", padx=(5, 5))
        self.condo_combo.bind("<<ComboboxSelected>>", lambda event: self.select_condominio())

        ttk.Button(top_frame, text="Adicionar condomínio", command=self.add_condominio, style="Add.TButton").pack(side="left", padx=4)
        ttk.Button(top_frame, text="Excluir condomínio", command=self.delete_condominio, style="Delete.TButton").pack(side="left", padx=4)
        ttk.Label(top_frame, text=f"v{APP_VERSION}", foreground="#666666").pack(side="right", padx=(8, 0))

        self.main_frame = ttk.Frame(self.root, padding=(10, 10, 10, 10))
        self.main_frame.pack(fill="both", expand=True)

        self.build_left_panel()
        self.build_center_panel()
        self.build_right_panel()
        self.root.update_idletasks()
        self.register_file_drop_targets()

    def build_left_panel(self):
        left = ttk.Frame(self.main_frame, width=250)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        section_labelframe = ttk.LabelFrame(left, text="Adicionar Etapa (Bloco)", padding=8)
        section_labelframe.pack(fill="x", pady=(0, 10))

        ttk.Button(section_labelframe, text="Adicionar etapa", command=self.add_section, style="Add.Compact.TButton").pack(
            fill="x", pady=(8, 0)
        )
        ttk.Button(section_labelframe, text="Excluir etapa atual", command=self.delete_current_section, style="Delete.Compact.TButton").pack(
            fill="x", pady=(8, 0)
        )

        current_frame = ttk.Frame(section_labelframe)
        current_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(current_frame, text="Etapa atual:").pack(side="left")
        self.current_section_font = tkfont.Font(size=11, weight="bold")
        self.current_section_label = ttk.Label(
            current_frame,
            text="Nenhuma etapa",
            font=self.current_section_font,
        )
        self.current_section_label.pack(side="left", padx=(5, 0))

        edit_section_frame = ttk.LabelFrame(left, text="Editar Etapa (Bloco)", padding=8)
        edit_section_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(
            edit_section_frame,
            text="Renomear etapa (Bloco) atual",
            command=self.rename_current_section,
            style="Compact.TButton",
        ).pack(fill="x", pady=(8, 0))
        section_order_actions = ttk.Frame(edit_section_frame)
        section_order_actions.pack(fill="x", pady=(8, 0))
        ttk.Button(
            section_order_actions,
            text="↑ Subir etapa",
            command=lambda: self.move_current_section(-1),
            style="Compact.TButton",
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(
            section_order_actions,
            text="↓ Descer etapa",
            command=lambda: self.move_current_section(1),
            style="Compact.TButton",
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        move_frame = ttk.LabelFrame(left, text="Mover fotos entre etapas", padding=8)
        move_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(
            move_frame,
            text="Selecione as fotos na Estrutura do Relatório e escolha a etapa/bloco de destino.",
            wraplength=210,
        ).pack(fill="x")
        self.move_section_var = tk.StringVar()
        self.move_section_combo = ttk.Combobox(
            move_frame,
            textvariable=self.move_section_var,
            state="readonly",
            width=28,
        )
        self.move_section_combo.pack(fill="x", pady=(8, 0))
        ttk.Button(
            move_frame,
            text="Mover fotos selecionadas",
            command=self.move_photos_to_section,
            style="Compact.TButton",
        ).pack(fill="x", pady=(8, 0))

    def build_center_panel(self):
        center = ttk.Frame(self.main_frame, width=520)
        center.pack(side="left", fill="both", expand=True, padx=(10, 10))

        tree_frame = ttk.LabelFrame(center, text="Estrutura do Relatório", padding=10)
        tree_frame.pack(fill="both", expand=True)

        columns = ("num", "anomaly", "file")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Etapa")
        self.tree.heading("num", text="Foto #")
        self.tree.heading("anomaly", text="Anomalia")
        self.tree.heading("file", text="Arquivo")
        self.tree.column("#0", width=130, anchor="w")
        self.tree.column("num", width=60, anchor="center")
        self.tree.column("anomaly", width=170, anchor="w")
        self.tree.column("file", width=280, anchor="w")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<<TreeviewSelect>>", lambda event: self.on_tree_select())
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_section_open)
        self.tree.bind("<<TreeviewClose>>", self.on_tree_section_close)
        self.tree.bind("<Delete>", self.on_tree_delete_key)
        self.tree.bind("<KP_Delete>", self.on_tree_delete_key)

        scrollbar = ttk.Scrollbar(tree_frame, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree_tag_style()

    def build_right_panel(self):
        right = ttk.Frame(self.main_frame, width=390)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        preview_frame = ttk.LabelFrame(right, text="Preview da foto", padding=8)
        preview_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.preview_label = ttk.Label(preview_frame, text="Selecione uma foto para ver o preview.", anchor="center")
        self.preview_label.pack(fill="both", expand=True, padx=10, pady=10)

        controls_frame = ttk.Frame(right)
        controls_frame.pack(fill="x")

        anomaly_frame = ttk.LabelFrame(controls_frame, text="Anomalia", padding=6)
        anomaly_frame.pack(fill="x", pady=(0, 6))

        self.anomaly_var = tk.StringVar()
        self.anomaly_combo = ttk.Combobox(
            anomaly_frame,
            textvariable=self.anomaly_var,
            values=self.anomalias,
            width=24,
        )
        self.anomaly_combo.pack(fill="x", pady=(0, 4))
        self.anomaly_combo.bind("<KeyRelease>", self.on_anomaly_combo_keyrelease)
        self.anomaly_combo.bind("<Return>", self.on_anomaly_combo_return)
        self.anomaly_combo.bind("<<ComboboxSelected>>", lambda event: self.assign_selected_anomaly())
        self.refresh_anomaly_combo()

        ttk.Button(
            anomaly_frame,
            text="Salvar anomalia na foto",
            command=self.save_anomaly,
            style="Save.Compact.TButton",
        ).pack(fill="x", pady=(0, 4))
        list_mgmt = ttk.Frame(anomaly_frame)
        list_mgmt.pack(fill="x")
        ttk.Label(
            list_mgmt,
            text="Gerenciar lista de anomalias:",
            font=tkfont.Font(size=8),
        ).pack(fill="x", pady=(0, 2))
        list_actions = ttk.Frame(list_mgmt)
        list_actions.pack(fill="x")
        ttk.Button(
            list_actions, text="Adicionar na lista", command=self.add_anomaly, style="Secondary.Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(
            list_actions, text="Excluir da lista", command=self.delete_anomaly, style="Delete.Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        drop_frame = ttk.LabelFrame(controls_frame, text="Inserir foto", padding=6)
        drop_frame.pack(fill="x", pady=(0, 6))
        self.drop_zone_label = tk.Label(
            drop_frame,
            text="Arraste a foto aqui\nou pressione Ctrl+V para colar",
            relief="ridge",
            bd=2,
            padx=12,
            pady=10,
            justify="center",
            bg="#f6f8fa",
        )
        self.drop_zone_label.pack(fill="x", pady=(0, 6))
        photo_input_actions = ttk.Frame(drop_frame)
        photo_input_actions.pack(fill="x")
        ttk.Button(
            photo_input_actions, text="Selecionar foto...", command=self.select_files, style="Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(
            photo_input_actions, text="Ctrl+V", command=self.paste_image, style="Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        action_frame = ttk.LabelFrame(controls_frame, text="Foto selecionada", padding=6)
        action_frame.pack(fill="x", pady=(0, 6))
        row_actions_1 = ttk.Frame(action_frame)
        row_actions_1.pack(fill="x", pady=(0, 4))
        ttk.Button(
            row_actions_1, text="Excluir foto", command=self.delete_selected_photo, style="Delete.Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(
            row_actions_1, text="↑ Subir", command=lambda: self.move_photo(-1), style="Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(2, 2))
        ttk.Button(
            row_actions_1, text="↓ Descer", command=lambda: self.move_photo(1), style="Compact.TButton"
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        tools_frame = ttk.LabelFrame(controls_frame, text="Finalizar", padding=6)
        tools_frame.pack(fill="x", pady=(0, 6))
        ttk.Button(
            tools_frame,
            text="Gerar relatório Word",
            command=self.generate_word_report,
            style="Secondary.Compact.TButton",
        ).pack(fill="x")

        flow_frame = ttk.LabelFrame(controls_frame, text="Última ação", padding=6)
        flow_frame.pack(fill="x")
        ttk.Label(
            flow_frame,
            textvariable=self.last_action_var,
            wraplength=300,
            justify="left",
        ).pack(fill="x")

        self.root.bind_all("<Control-v>", lambda event: self.paste_image())

    def tree_tag_style(self):
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=24)
        style.configure("Treeview.Heading", font=(None, 10, "bold"))
        self.tree.tag_configure("active_section", background="#e3f2fd")

    def setup_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self._configure_colored_button_style(
            style,
            "Save.Compact.TButton",
            background="#2e7d32",
            active="#43a047",
            pressed="#1b5e20",
            padding=(6, 4),
        )
        self._configure_colored_button_style(
            style,
            "Add.TButton",
            background="#2e7d32",
            active="#43a047",
            pressed="#1b5e20",
            padding=(10, 5),
        )
        self._configure_colored_button_style(
            style,
            "Delete.TButton",
            background="#c62828",
            active="#e53935",
            pressed="#b71c1c",
            padding=(10, 5),
        )
        self._configure_colored_button_style(
            style,
            "Add.Compact.TButton",
            background="#2e7d32",
            active="#43a047",
            pressed="#1b5e20",
            padding=(4, 2),
        )
        self._configure_colored_button_style(
            style,
            "Delete.Compact.TButton",
            background="#c62828",
            active="#e53935",
            pressed="#b71c1c",
            padding=(4, 2),
        )
        style.configure("Compact.TButton", padding=(4, 2))
        style.configure(
            "Secondary.Compact.TButton",
            background="#eceff1",
            foreground="#37474f",
            borderwidth=1,
            focuscolor="none",
            padding=(4, 2),
        )
        style.map(
            "Secondary.Compact.TButton",
            background=[("active", "#cfd8dc"), ("pressed", "#b0bec5")],
            foreground=[("active", "#263238"), ("pressed", "#263238")],
        )

    def _configure_colored_button_style(
        self,
        style,
        name,
        *,
        background,
        active,
        pressed,
        padding,
    ):
        style.configure(
            name,
            background=background,
            foreground="white",
            borderwidth=1,
            focuscolor="none",
            padding=padding,
        )
        style.map(
            name,
            background=[("active", active), ("pressed", pressed)],
            foreground=[("active", "white"), ("pressed", "white")],
        )

    def register_file_drop_targets(self):
        try:
            from tkinterdnd2 import DND_FILES
        except ImportError:
            messagebox.showwarning(
                "Arrastar arquivos",
                "O pacote 'tkinterdnd2' não está instalado ou está desatualizado",
                parent=self.root,
            )
            return
        if not hasattr(self.drop_zone_label, "drop_target_register"):
            messagebox.showwarning(
                "Arrastar arquivos",
                "Arrastar arquivos requer iniciar o programa com suporte a DnD.\n"
                "Reinstale tkinterdnd2 e abra o app novamente.",
                parent=self.root,
            )
            return
        drop_zone = cast(_TkinterDnDDropTarget, self.drop_zone_label)
        drop_zone.drop_target_register(DND_FILES)
        drop_zone.dnd_bind("<<Drop>>", self._on_dnd_drop)

    def _on_dnd_drop(self, event):
        paths = [str(path) for path in self.root.tk.splitlist(event.data)]
        self.on_files_dropped(paths)

    def import_image_paths(self, file_paths):
        allowed = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        imported = []
        for raw_path in file_paths:
            source = Path(raw_path)
            if not source.is_file():
                continue
            suffix = source.suffix.lower()
            if suffix not in allowed:
                continue
            try:
                if source.parent.resolve() == IMAGE_DIR.resolve():
                    imported.append(str(source.resolve()))
                    continue
                destination = IMAGE_DIR / f"{source.stem}_{uuid.uuid4().hex[:8]}{suffix}"
                shutil.copy2(source, destination)
                imported.append(str(destination.resolve()))
            except OSError:
                continue
        return imported

    def on_files_dropped(self, file_paths):
        if not self.current_cond:
            messagebox.showwarning("Aviso", "Selecione um condomínio antes de soltar arquivos.")
            return
        valid_paths = self.import_image_paths(file_paths)
        if not valid_paths:
            messagebox.showwarning(
                "Aviso",
                "Nenhuma imagem válida encontrada nos arquivos arrastados.",
            )
            return
        self.add_photos(valid_paths)

    def refresh_condominios(self):
        condos = sorted(self.data["condominios"].keys())
        self.condo_combo["values"] = condos
        current = self.data.get("current_condominio")
        if current in condos:
            self.condo_var.set(str(current))
            self.select_condominio()
        elif condos:
            self.condo_var.set(str(condos[0]))
            self.select_condominio()
        else:
            self.condo_var.set(str("Nenhum condomínio selecionado"))
            self.current_cond = None
            self.current_section_index = 0
            self.update_current_section_label()
            self.tree.delete(*self.tree.get_children())
            self.refresh_move_section_targets()

    def select_condominio(self):
        name = self.condo_var.get().strip()
        if not name:
            return
        self.data["current_condominio"] = name
        self.current_cond = self.data["condominios"].setdefault(
            name,
            {
                "sections": [],
            },
        )
        self.current_section_index = 0
        self.save_data()
        self.refresh_tree()

    def add_condominio(self):
        name = simpledialog.askstring("Adicionar condomínio", "Nome do condomínio:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.data["condominios"]:
            messagebox.showwarning("Atenção", "Este condomínio já existe.")
            return
        self.data["condominios"][name] = {"sections": []}
        self.data["current_condominio"] = name
        self.save_data()
        self.refresh_condominios()
        self.condo_var.set(name)
        self.select_condominio()
        self.set_last_action(f"Condomínio '{name}' criado.")

    def delete_condominio(self):
        if not self.current_cond:
            return
        name = self.condo_var.get()
        if not name:
            return
        answer = messagebox.askyesno(
            "Excluir condomínio",
            f"Deseja realmente excluir o condomínio {name}? Esta ação não pode ser desfeita.",
        )
        if answer:
            self.data["condominios"].pop(name, None)
            if self.data.get("current_condominio") == name:
                self.data["current_condominio"] = None
            self.save_data()
            self.current_cond = None
            self.refresh_condominios()
            self.set_last_action(f"Condomínio '{name}' excluído.")

    def add_section(self):
        if not self.current_cond:
            return
        name = simpledialog.askstring(
            "Nova seção",
            "Nome da nova seção (ex: Torre A, Portaria, Bloco 1):",
            parent=self.root,
        )
        if not name:
            return
        name = name.strip()
        if not name:
            return
        self.current_cond["sections"].append({"name": name, "photos": []})
        self.current_section_index = len(self.current_cond["sections"]) - 1
        self.save_data()
        self.refresh_tree()
        self.focus_current_section_in_tree()
        self.set_last_action(f"Bloco '{name}' criado.")

    def add_anomaly(self):
        name = simpledialog.askstring("Nova anomalia", "Nome da anomalia:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        existing = {item.casefold() for item in self.anomalias}
        if name.casefold() in existing:
            messagebox.showwarning("Atenção", "Essa anomalia já existe.")
            return
        self.anomalias.append(name)
        self.anomalias.sort(key=str.casefold)
        self.save_anomalias()
        self.refresh_anomaly_combo()
        self.anomaly_var.set(name)
        self.set_last_action(f"Anomalia '{name}' adicionada à lista.")

    def delete_anomaly(self):
        current = self.anomaly_var.get().strip()
        if not current:
            messagebox.showwarning("Atenção", "Selecione a anomalia que deseja excluir.")
            return
        if current not in self.anomalias:
            return
        if not messagebox.askyesno(
            "Excluir anomalia",
            f"Deseja excluir a anomalia '{current}'?",
            parent=self.root,
        ):
            return
        self.anomalias = [item for item in self.anomalias if item != current]
        self.save_anomalias()
        self.anomaly_var.set("")
        self.refresh_anomaly_combo()
        self.set_last_action(f"Anomalia '{current}' excluída da lista.")

    def find_photos_without_anomaly(self):
        missing = []
        if not self.current_cond:
            return missing
        for section in self.current_cond.get("sections", []):
            section_name = section.get("name", "Sem nome")
            for photo in section.get("photos", []):
                if not str(photo.get("anomaly", "")).strip():
                    missing.append(
                        (
                            section_name,
                            photo.get("order", "?"),
                            os.path.basename(str(photo.get("path", ""))),
                        )
                    )
        return missing

    def generate_word_report(self):
        if not self.current_cond:
            messagebox.showwarning("Aviso", "Selecione um condomínio antes de gerar o relatório.")
            return

        condo_name = self.condo_var.get().strip()
        missing = self.find_photos_without_anomaly()
        if missing:
            lines = [
                f"• Etapa '{section}', foto {order} ({filename})"
                for section, order, filename in missing[:15]
            ]
            extra = len(missing) - 15
            if extra > 0:
                lines.append(f"• ... e mais {extra} foto(s).")
            messagebox.showerror(
                "Fotos sem anomalia selecionada",
                "Todas as fotos precisam ter uma anomalia selecionada antes de gerar o Word. Verificar as fotos abaixo:\n\n"
                + "\n".join(lines),
                parent=self.root,
            )
            self.set_last_action(
                f"Relatório Word bloqueado: {len(missing)} foto(s) sem anomalia em '{condo_name}'."
            )
            return

        total_photos = len(self.get_flat_photos())
        if total_photos == 0:
            messagebox.showwarning(
                "Aviso",
                "Não há fotos no condomínio selecionado. Adicione fotos antes de gerar o relatório.",
                parent=self.root,
            )
            return

        try:
            from gerar_relatorio_word import gerar_relatorio

            output_path = gerar_relatorio(
                condo_name,
                self.current_cond,
                parent=self.root,
            )
        except RuntimeError as exc:
            if "cancelado" in str(exc).casefold():
                self.set_last_action(f"Geração do relatório Word cancelada para '{condo_name}'.")
                return
            messagebox.showerror("Erro ao gerar relatório", str(exc), parent=self.root)
            self.set_last_action(f"Erro ao gerar relatório Word para '{condo_name}'.")
            return
        except Exception as exc:
            messagebox.showerror("Erro ao gerar relatório", str(exc), parent=self.root)
            self.set_last_action(f"Erro ao gerar relatório Word para '{condo_name}'.")
            return

        self.set_last_action(f"Relatório Word gerado: {output_path.name}")
        messagebox.showinfo(
            "Relatório gerado",
            f"O relatório foi salvo e aberto:\n{output_path}",
            parent=self.root,
        )

    def delete_current_section(self):
        if not self.current_cond:
            return
        sections = self.current_cond.get("sections", [])
        if not sections:
            return
        section = sections[self.current_section_index]
        section_name = section["name"]
        if not messagebox.askyesno(
            "Excluir etapa",
            f"Deseja excluir a etapa '{section_name}' e todas as fotos dela?",
            parent=self.root,
        ):
            return
        sections.pop(self.current_section_index)
        self.collapsed_section_names.discard(section_name)
        if not sections:
            self.current_section_index = 0
        elif self.current_section_index >= len(sections):
            self.current_section_index = len(sections) - 1
        self.renumber_photos()
        self.save_data()
        self.refresh_tree()
        self.preview_label.config(image="", text="Selecione uma foto para ver o preview.")
        self.preview_image = None
        self.set_last_action(f"Bloco '{section_name}' excluído.")

    def rename_current_section(self):
        if not self.current_cond:
            return
        sections = self.current_cond.get("sections", [])
        if not sections:
            messagebox.showwarning("Atenção", "Não há etapas para renomear.", parent=self.root)
            return
        section = sections[self.current_section_index]
        old_name = section["name"]
        new_name = simpledialog.askstring(
            "Renomear etapa",
            "Novo nome da etapa:",
            initialvalue=old_name,
            parent=self.root,
        )
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        if any(item["name"] == new_name for item in sections):
            messagebox.showwarning("Atenção", "Já existe uma etapa com esse nome.", parent=self.root)
            return
        if old_name in self.collapsed_section_names:
            self.collapsed_section_names.discard(old_name)
            self.collapsed_section_names.add(new_name)
        section["name"] = new_name
        self.save_data()
        self.refresh_tree()
        self.focus_current_section_in_tree()
        self.set_last_action(f"Bloco renomeado de '{old_name}' para '{new_name}'.")

    def move_current_section(self, direction):
        if not self.current_cond:
            return
        sections = self.current_cond.get("sections", [])
        if not sections:
            return
        index = self.current_section_index
        target = index + direction
        if target < 0 or target >= len(sections):
            return
        sections[index], sections[target] = sections[target], sections[index]
        self.current_section_index = target
        self.renumber_photos()
        self.save_data()
        self.refresh_tree()
        self.focus_current_section_in_tree()
        section_name = sections[self.current_section_index]["name"]
        if direction < 0:
            self.set_last_action(f"Etapa '{section_name}' movido para cima.")
        else:
            self.set_last_action(f"Etapa '{section_name}' movido para baixo.")

    def on_tree_section_open(self, event):
        item = self.tree.focus()
        if not item or not str(item).startswith("section-"):
            return
        section_name = self.tree.item(item, "text")
        if section_name:
            self.collapsed_section_names.discard(section_name)

    def on_tree_section_close(self, event):
        item = self.tree.focus()
        if not item or not str(item).startswith("section-"):
            return
        section_name = self.tree.item(item, "text")
        if section_name:
            self.collapsed_section_names.add(section_name)

    def section_id_to_index(self, section_id):
        if not str(section_id).startswith("section-"):
            return None
        try:
            return int(str(section_id).split("-", 1)[1])
        except (IndexError, ValueError):
            return None

    def apply_active_section_highlight(self):
        if not self.current_cond:
            return
        for index in range(len(self.current_cond.get("sections", []))):
            section_id = f"section-{index}"
            if not self.tree.exists(section_id):
                continue
            tags = ("section", "active_section") if index == self.current_section_index else ("section",)
            self.tree.item(section_id, tags=tags)

    def set_active_section(self, index, *, focus_tree=False, clear_preview=False):
        if not self.current_cond:
            return
        sections = self.current_cond.get("sections", [])
        if not sections or index < 0 or index >= len(sections):
            return
        self.current_section_index = index
        self.update_current_section_label()
        self.apply_active_section_highlight()
        if focus_tree:
            self.focus_current_section_in_tree()
        if clear_preview:
            self.preview_label.config(text="Selecione uma foto para ver o preview.")
            self.preview_image = None

    def focus_current_section_in_tree(self):
        if not self.current_cond:
            return
        sections = self.current_cond.get("sections", [])
        if not sections:
            return
        section_id = f"section-{self.current_section_index}"
        if not self.tree.exists(section_id):
            return
        self._handling_tree_select = True
        try:
            self.tree.selection_set(section_id)
            self.tree.focus(section_id)
            self.tree.see(section_id)
        finally:
            self._handling_tree_select = False

    def update_current_section_label(self):
        if not self.current_cond:
            self.current_section_label.config(text="Nenhum condomínio")
            return
        sections = self.current_cond.get("sections", [])
        if not sections:
            self.current_section_label.config(text="Sem etapas")
            return
        section = sections[self.current_section_index]
        self.current_section_label.config(text=section["name"])

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.current_cond:
            return

        sections = self.current_cond.get("sections", [])
        for index, section in enumerate(sections):
            section_text = section["name"]
            section_id = f"section-{index}"
            section_tags = ("section", "active_section") if index == self.current_section_index else ("section",)
            self.tree.insert("", "end", section_id, text=section_text, values=("", "", ""), tags=section_tags)
            self.tree.item(
                section_id,
                open=section_text not in self.collapsed_section_names,
            )
            for photo in section.get("photos", []):
                row_id = photo["id"]
                self.tree.insert(
                    section_id,
                    "end",
                    row_id,
                    text="",
                    values=(photo["order"], photo["anomaly"], os.path.basename(photo["path"])),
                    tags=("photo",),
                )
        self.update_current_section_label()
        self.refresh_move_section_targets()

    def refresh_move_section_targets(self):
        if not hasattr(self, "move_section_combo"):
            return
        if not self.current_cond:
            self.move_section_combo["values"] = []
            self.move_section_var.set("")
            return
        section_names = [section["name"] for section in self.current_cond.get("sections", [])]
        self.move_section_combo["values"] = section_names
        current = self.move_section_var.get()
        if current not in section_names:
            self.move_section_var.set(section_names[0] if section_names else "")

    def get_flat_photos(self):
        photos = []
        if not self.current_cond:
            return photos
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                photos.append(photo)
        return photos

    def renumber_photos(self):
        if not self.current_cond:
            return
        count = 1
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                photo["order"] = count
                count += 1

    def select_files(self):
        if not self.current_cond:
            messagebox.showwarning("Aviso", "Selecione um condomínio antes de incluir fotos.")
            return
        file_paths = filedialog.askopenfilenames(
            title="Selecionar fotos",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("Todos os arquivos", "*")],
        )
        if file_paths:
            imported = self.import_image_paths(file_paths)
            if imported:
                self.add_photos(imported)

    def add_photos(self, file_paths):
        section = self.ensure_current_section()
        if section is None:
            return
        last_photo_id = None
        added_photo_ids = []
        for path in file_paths:
            photo = {
                "id": str(uuid.uuid4()),
                "path": str(path),
                "anomaly": "",
                "order": len(self.get_flat_photos()) + 1,
            }
            section["photos"].append(photo)
            last_photo_id = photo["id"]
            added_photo_ids.append(photo["id"])
        self.renumber_photos()
        self.save_data()
        self.refresh_tree()
        if last_photo_id:
            self._handling_tree_select = True
            try:
                self.tree.selection_set(last_photo_id)
                self.tree.focus(last_photo_id)
                self.tree.see(last_photo_id)
                self.load_photo_preview(last_photo_id)
            finally:
                self._handling_tree_select = False
        added_orders = []
        for photo_id in added_photo_ids:
            photo = self.find_photo_by_id(photo_id)
            if photo:
                added_orders.append(photo["order"])
        if len(added_orders) == 1:
            self.set_last_action(f"Foto {added_orders[0]} inserida na etapa '{section['name']}'.")
        elif added_orders:
            self.set_last_action(
                f"Fotos {min(added_orders)} a {max(added_orders)} inseridas na etapa '{section['name']}'."
            )

    def ensure_current_section(self):
        if not self.current_cond:
            return None
        sections = self.current_cond.setdefault("sections", [])
        if not sections:
            messagebox.showwarning("Aviso", "Crie uma etapa (bloco) antes de adicionar fotos.")
            return None
        if self.current_section_index >= len(sections):
            self.current_section_index = len(sections) - 1
        return sections[self.current_section_index]

    def get_selected_photo_ids(self):
        return [item_id for item_id in self.tree.selection() if self.find_photo_by_id(item_id)]

    def get_focused_photo_id(self):
        focused = self.tree.focus()
        if focused and self.find_photo_by_id(focused):
            return focused
        photo_ids = self.get_selected_photo_ids()
        return photo_ids[0] if photo_ids else None

    def iter_photo_ids_in_display_order(self):
        if not self.current_cond:
            return []
        photo_ids = []
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                photo_ids.append(photo["id"])
        return photo_ids

    def get_next_photo_id(self, current_photo_id):
        photo_ids = self.iter_photo_ids_in_display_order()
        if not photo_ids:
            return None
        if current_photo_id not in photo_ids:
            return photo_ids[0]
        next_index = photo_ids.index(current_photo_id) + 1
        if next_index < len(photo_ids):
            return photo_ids[next_index]
        return None

    def focus_photo_for_anomaly_entry(self, photo_id, *, clear_anomaly_field=True):
        parent_id = self.tree.parent(photo_id)
        index = self.section_id_to_index(parent_id)
        if index is not None and index != self.current_section_index:
            self.current_section_index = index
            self.update_current_section_label()
            self.apply_active_section_highlight()

        self._handling_tree_select = True
        try:
            self.tree.selection_set(photo_id)
            self.tree.focus(photo_id)
            self.tree.see(photo_id)
            self.load_photo_preview(photo_id)
            if clear_anomaly_field:
                self.anomaly_var.set("")
            self.refresh_anomaly_combo()
            self.anomaly_combo.focus_set()
        finally:
            self._handling_tree_select = False

    def advance_to_next_photo_after_anomaly(self, current_photo_id):
        next_id = self.get_next_photo_id(current_photo_id)
        if next_id:
            self.focus_photo_for_anomaly_entry(next_id)
            photo = self.find_photo_by_id(next_id)
            order = photo["order"] if photo else "?"
        else:
            self.anomaly_var.set("")
            self.refresh_anomaly_combo()
            self.anomaly_combo.focus_set()

    def on_tree_delete_key(self, event):
        self.delete_selected_photo()
        return "break"

    def on_tree_select(self):
        if self._handling_tree_select:
            return
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        if str(item_id).startswith("section-") and len(selected) == 1:
            index = self.section_id_to_index(item_id)
            if index is not None:
                self.set_active_section(index, clear_preview=True)
            return
        preview_id = self.get_focused_photo_id()
        if preview_id:
            parent_id = self.tree.parent(preview_id)
            index = self.section_id_to_index(parent_id)
            if index is not None and index != self.current_section_index:
                self.set_active_section(index)
            self.load_photo_preview(preview_id)
        else:
            self.preview_label.config(text="Selecione uma foto para ver o preview.")
            self.preview_image = None

    def load_photo_preview(self, photo_id):
        photo = self.find_photo_by_id(photo_id)
        if not photo:
            return
        self.anomaly_var.set(photo.get("anomaly", ""))
        image_path = Path(photo["path"])
        if image_path.exists():
            try:
                image = Image.open(image_path)
                self.preview_label.update_idletasks()
                max_width = max(220, self.preview_label.winfo_width() - 20)
                max_height = max(220, self.preview_label.winfo_height() - 20)
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(image)
                self.preview_label.config(image=self.preview_image, text="")
            except Exception as exc:
                self.preview_label.config(text=f"Não foi possível carregar a imagem: {exc}")
                self.preview_image = None
        else:
            self.preview_label.config(text="Arquivo de imagem não encontrado.")
            self.preview_image = None

    def find_photo_by_id(self, photo_id):
        if not self.current_cond:
            return None
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                if photo["id"] == photo_id:
                    return photo
        return None

    def on_anomaly_combo_keyrelease(self, event):
        if event.keysym in (
            "Up",
            "Down",
            "Left",
            "Right",
            "Return",
            "Tab",
            "Escape",
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
        ):
            return
        self.filter_anomaly_combo()

    def on_anomaly_combo_return(self, event):
        self.confirm_anomaly_from_combo()
        return "break"

    def confirm_anomaly_from_combo(self):
        typed = self.anomaly_var.get().strip()
        if not typed:
            return
        resolved = self.resolve_anomaly_name(typed)
        if not resolved:
            messagebox.showwarning(
                "Atenção",
                f"Nenhuma anomalia encontrada para '{typed}'.\n"
                "Digite mais letras ou escolha um item da lista.",
                parent=self.root,
            )
            return
        self.anomaly_var.set(resolved)
        self.save_anomaly(advance_to_next=True)

    def save_anomaly(self, *, advance_to_next=False):
        item_id = self.get_focused_photo_id()
        if not item_id:
            messagebox.showwarning("Atenção", "Selecione a foto para associar uma anomalia.")
            return False
        photo = self.find_photo_by_id(item_id)
        if not photo:
            messagebox.showwarning("Atenção", "Selecione uma foto válida.")
            return False
        typed = self.anomaly_var.get().strip()
        if not typed:
            messagebox.showwarning("Atenção", "Selecione uma anomalia antes de salvar.")
            return False
        anomaly_name = self.resolve_anomaly_name(typed)
        if not anomaly_name:
            messagebox.showwarning(
                "Atenção",
                f"Nenhuma anomalia encontrada para '{typed}'.\n"
                "Digite mais letras ou escolha um item da lista.",
                parent=self.root,
            )
            return False
        self.anomaly_var.set(anomaly_name)
        photo["anomaly"] = anomaly_name
        self.save_data()
        self.refresh_tree()
        self.tree.selection_set(item_id)
        self.anomaly_combo["values"] = self.anomalias
        self.set_last_action(f"Foto {photo['order']} - {anomaly_name}")
        if advance_to_next:
            self.advance_to_next_photo_after_anomaly(item_id)
        return True

    def assign_selected_anomaly(self):
        if not self.tree.selection():
            return
        self.save_anomaly(advance_to_next=False)

    def paste_image(self):
        if not self.current_cond:
            messagebox.showwarning("Aviso", "Selecione um condomínio antes de colar imagens.")
            return
        image = ImageGrab.grabclipboard()
        if image is None:
            messagebox.showwarning(
                "Aviso",
                "Não há imagem na área de transferência. Copie uma imagem antes de usar Ctrl+V.",
            )
            return
        if isinstance(image, Image.Image):
            destination = IMAGE_DIR / f"clipboard_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
            image.save(destination)
            self.add_photos([str(destination)])
            return
        if isinstance(image, list):
            file_paths = [str(path) for path in image if Path(path).exists()]
            if file_paths:
                self.add_photos(file_paths)
                return
        messagebox.showwarning(
            "Aviso",
            "A imagem na área de transferência não pôde ser processada. Cole um arquivo de imagem ou use o seletor de arquivos.",
        )

    def delete_selected_photo(self):
        photo_ids = self.get_selected_photo_ids()
        if not photo_ids:
            if self.tree.selection():
                messagebox.showwarning("Nenhuma foto selecionada",
                "Selecione uma foto para excluir. Para excluir um bloco, utilize 'Excluir etapa atual', à esquerda.",
                parent=self.root,
                icon="warning")
            return
        count = len(photo_ids)
        if count == 1:
            confirm = "Deseja excluir esta foto?"
        else:
            confirm = f"Deseja excluir as {count} fotos selecionadas?"
        if not messagebox.askyesno("Excluir foto", confirm, parent=self.root):
            return
        if not self.current_cond:
            return
        id_set = set(photo_ids)
        removed_orders = []
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                if photo["id"] in id_set:
                    removed_orders.append(photo["order"])
            section["photos"] = [photo for photo in section["photos"] if photo["id"] not in id_set]
        self.renumber_photos()
        self.save_data()
        self.refresh_tree()
        self.preview_label.config(image="", text="Selecione uma foto para ver o preview.")
        self.preview_image = None
        if count == 1:
            self.set_last_action(f"Foto {removed_orders[0]} excluída.")
        else:
            self.set_last_action(f"{count} fotos excluídas.")

    def move_photo(self, direction):
        item_id = self.get_focused_photo_id()
        if not item_id:
            messagebox.showwarning("Selecione uma foto para mover.")
            return
        if len(self.get_selected_photo_ids()) > 1:
            messagebox.showwarning(
                "Atenção",
                "Selecione apenas uma foto para mover.",
                parent=self.root,
            )
            return
        if not self.current_cond:
            return
        for section in self.current_cond.get("sections", []):
            photos = section.get("photos", [])
            for index, photo in enumerate(photos):
                if photo["id"] == item_id:
                    target = index + direction
                    if 0 <= target < len(photos):
                        photos[index], photos[target] = photos[target], photos[index]
                        self.renumber_photos()
                        self.save_data()
                        self.refresh_tree()
                        self.tree.selection_set(item_id)
                    return

    def move_photos_to_section(self):
        photo_ids = self.get_selected_photo_ids()
        if not photo_ids:
            messagebox.showwarning(
                "Atenção",
                "Selecione uma ou mais fotos na Estrutura do Relatório para mover.",
                parent=self.root,
            )
            return
        if not self.current_cond:
            return
        sections = self.current_cond.get("sections", [])
        if not sections:
            messagebox.showwarning("Atenção", "Não há etapas disponíveis.", parent=self.root)
            return
        target_name = self.move_section_var.get().strip()
        if not target_name:
            messagebox.showwarning("Atenção", "Selecione a etapa de destino.", parent=self.root)
            return
        target_section = next((section for section in sections if section["name"] == target_name), None)
        if target_section is None:
            messagebox.showwarning("Atenção", "Etapa de destino inválida.", parent=self.root)
            return
        photo_id_set = set(photo_ids)
        photos_to_move = []
        for photo_id in self.iter_photo_ids_in_display_order():
            if photo_id in photo_id_set:
                photo = self.find_photo_by_id(photo_id)
                if photo:
                    photos_to_move.append(photo)
        if not photos_to_move:
            return
        source_names = {
            section["name"]
            for section in sections
            for photo in section.get("photos", [])
            if photo["id"] in photo_id_set
        }
        if source_names == {target_name}:
            messagebox.showinfo(
                "Atenção",
                f"As fotos selecionadas já estão na etapa '{target_name}'.",
                parent=self.root,
            )
            return
        for section in sections:
            section["photos"] = [photo for photo in section.get("photos", []) if photo["id"] not in photo_id_set]
        target_section["photos"].extend(photos_to_move)
        self.renumber_photos()
        self.save_data()
        self.refresh_tree()
        self._handling_tree_select = True
        try:
            self.tree.selection_set(photo_ids)
            self.tree.focus(photo_ids[0])
            self.tree.see(photo_ids[0])
            self.load_photo_preview(photo_ids[0])
        finally:
            self._handling_tree_select = False
        moved_orders = [photo["order"] for photo in photos_to_move]
        count = len(photos_to_move)
        if count == 1:
            self.set_last_action(f"Foto {moved_orders[0]} movida para '{target_name}'.")
        else:
            self.set_last_action(
                f"Fotos {min(moved_orders)} a {max(moved_orders)} movidas para '{target_name}'."
            )

    def get_section_name_by_photo_id(self, photo_id):
        if not self.current_cond:
            return None
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                if photo["id"] == photo_id:
                    return section.get("name", "")
        return None


if __name__ == "__main__":
    try:
        from tkinterdnd2 import TkinterDnD

        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    app = RelatorioFotograficoApp(root)
    root.mainloop()
