import ctypes
import json
import os
import sys
import uuid
import time
from ctypes import wintypes
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageGrab, ImageTk

DATA_FILE = Path("condominios.json")
ANOMALY_FILE = Path("anomalias.json")
IMAGE_DIR = Path("imagens")
AUTOSAVE_MS = 5 * 60 * 1000
DEFAULT_ANOMALIAS = [
    "Fissuras",
    "Pisos soltos",
    "Revestimentos soltos",
    "Impermeabilização comprometida",
    "Rachaduras",
    "Trincas",
    "Reboque ruim",
    "Infiltração pela cobertura"
]


class RelatorioFotograficoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerador de Relatórios Fotográficos")
        self.root.geometry("1240x760")
        self.root.minsize(1100, 700)
        self.root.state("zoomed")
        self._drop_proc = None
        self._old_wnd_proc = None

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
        self.anomaly_combo["values"] = self.anomalias
        current = self.anomaly_var.get().strip()
        if current and current not in self.anomalias:
            self.anomaly_var.set("")

    def set_last_action(self, message):
        self.last_action_var.set(message)

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

        ttk.Button(top_frame, text="Adicionar", command=self.add_condominio, style="Add.TButton").pack(side="left", padx=4)
        ttk.Button(top_frame, text="Excluir", command=self.delete_condominio, style="Delete.TButton").pack(side="left", padx=4)

        self.main_frame = ttk.Frame(self.root, padding=(10, 10, 10, 10))
        self.main_frame.pack(fill="both", expand=True)

        self.build_left_panel()
        self.build_center_panel()
        self.build_right_panel()
        self.root.update_idletasks()
        self.register_file_drop(self.drop_zone_label, self.on_files_dropped)

    def build_left_panel(self):
        left = ttk.Frame(self.main_frame, width=250)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        section_labelframe = ttk.LabelFrame(left, text="Adicionar Etapa (Bloco)", padding=8)
        section_labelframe.pack(fill="x", pady=(0, 10))

        ttk.Label(
            section_labelframe,
            text="Digite o nome completo da etapa ao adicionar (exemplo: Torre A, Portaria, Bloco 1)",
            wraplength=210,
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Button(section_labelframe, text="Adicionar etapa", command=self.add_section, style="Add.Compact.TButton").grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )
        ttk.Button(section_labelframe, text="Excluir etapa atual", command=self.delete_current_section, style="Delete.Compact.TButton").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )

        navigation = ttk.Frame(section_labelframe)
        navigation.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(navigation, text="Anterior", command=self.goto_previous_section, style="Compact.TButton").pack(
            side="left", expand=True, fill="x"
        )
        ttk.Button(navigation, text="Próxima", command=self.goto_next_section, style="Compact.TButton").pack(
            side="left", expand=True, fill="x", padx=(5, 0)
        )

        current_frame = ttk.Frame(section_labelframe)
        current_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Label(current_frame, text="Etapa atual:").pack(side="left")
        self.current_section_font = tkfont.Font(weight="bold")
        self.current_section_label = ttk.Label(
            current_frame,
            text="Nenhuma etapa",
            font=self.current_section_font,
        )
        self.current_section_label.pack(side="left", padx=(5, 0))

        ttk.Button(section_labelframe, text="Reordenar fotos", command=self.refresh_tree, style="Compact.TButton").grid(
            row=5, column=0, columnspan=3, sticky="ew", pady=(10, 0)
        )

    def build_center_panel(self):
        center = ttk.Frame(self.main_frame, width=520)
        center.pack(side="left", fill="both", expand=True, padx=(10, 10))

        tree_frame = ttk.LabelFrame(center, text="Estrutura do relatório", padding=10)
        tree_frame.pack(fill="both", expand=True)

        columns = ("num", "anomaly", "file")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", selectmode="browse")
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
            state="readonly",
            width=24,
        )
        self.anomaly_combo.pack(fill="x", pady=(0, 4))
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
            font=(None, 8),
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
            row_actions_1, text="Excluir", command=self.delete_selected_photo, style="Delete.Compact.TButton"
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

    def register_file_drop(self, widget, callback):
        if sys.platform != "win32":
            return
        try:
            widget.update_idletasks()
            hwnd = widget.winfo_id()
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            shell32.DragAcceptFiles(hwnd, True)
            GWL_WNDPROC = -4
            WNDPROC = ctypes.WINFUNCTYPE(
                wintypes.LRESULT,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )

            def _wnd_proc(hwnd, msg, wparam, lparam):
                if msg == 0x233:
                    count = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    files = []
                    buf = ctypes.create_unicode_buffer(260)
                    for i in range(count):
                        shell32.DragQueryFileW(wparam, i, buf, 260)
                        files.append(buf.value)
                    shell32.DragFinish(wparam)
                    self.root.after(10, lambda: callback(files))
                    return 0
                return user32.CallWindowProcW(self._old_wnd_proc, hwnd, msg, wparam, lparam)

            self._drop_proc = WNDPROC(_wnd_proc)
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                self._old_wnd_proc = user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, self._drop_proc)
            else:
                self._old_wnd_proc = user32.SetWindowLongW(hwnd, GWL_WNDPROC, self._drop_proc)
        except Exception:
            pass

    def on_files_dropped(self, file_paths):
        if not self.current_cond:
            messagebox.showwarning("Aviso", "Selecione um condomínio antes de soltar arquivos.")
            return
        valid_paths = [
            p for p in file_paths if Path(p).suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".gif")
        ]
        if not valid_paths:
            messagebox.showwarning(
                "Aviso",
                "Nenhuma imagem válida encontrada nos arquivos arrastados."
            )
            return
        self.add_photos(valid_paths)

    def refresh_condominios(self):
        condos = sorted(self.data["condominios"].keys())
        self.condo_combo["values"] = condos
        current = self.data.get("current_condominio")
        if current in condos:
            self.condo_var.set(current)
            self.select_condominio()
        elif condos:
            self.condo_var.set(condos[0])
            self.select_condominio()
        else:
            self.condo_var.set("")
            self.current_cond = None
            self.current_section_index = 0
            self.update_current_section_label()
            self.tree.delete(*self.tree.get_children())

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
            "Nome da nova seção (ex: 1, Torre A, Portaria):",
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

    def generate_word_report(self):
        script_path = Path("gerar_relatorio_word.py")
        condo_name = self.condo_var.get().strip() or "sem condomínio"
        if not script_path.exists():
            messagebox.showinfo(
                "Gerar relatório Word",
                "O script 'gerar_relatorio_word.py' ainda não foi criado.",
            )
            self.set_last_action(f"Relatório Word solicitado ({condo_name}) — script pendente.")
            return
        messagebox.showinfo(
            "Gerar relatório Word",
            "Base pronta: conecte aqui a chamada do script de geração do Word.",
        )
        self.set_last_action(f"Relatório Word solicitado para '{condo_name}'.")

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

    def goto_previous_section(self):
        if not self.current_cond:
            return
        if self.current_section_index > 0:
            self.set_active_section(
                self.current_section_index - 1,
                focus_tree=True,
                clear_preview=True,
            )

    def goto_next_section(self):
        if not self.current_cond:
            return
        if self.current_section_index < len(self.current_cond["sections"]) - 1:
            self.set_active_section(
                self.current_section_index + 1,
                focus_tree=True,
                clear_preview=True,
            )

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
            self.add_photos(file_paths)

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
            self.tree.selection_set(last_photo_id)
            self.load_photo_preview(last_photo_id)
        added_orders = []
        for photo_id in added_photo_ids:
            photo = self.find_photo_by_id(photo_id)
            if photo:
                added_orders.append(photo["order"])
        if len(added_orders) == 1:
            self.set_last_action(f"Foto {added_orders[0]} inserida no bloco '{section['name']}'.")
        elif added_orders:
            self.set_last_action(
                f"Fotos {min(added_orders)} a {max(added_orders)} inseridas no bloco '{section['name']}'."
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

    def on_tree_select(self):
        if self._handling_tree_select:
            return
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        if str(item_id).startswith("section-"):
            index = self.section_id_to_index(item_id)
            if index is not None:
                self.set_active_section(index, clear_preview=True)
            return
        if self.find_photo_by_id(item_id):
            parent_id = self.tree.parent(item_id)
            index = self.section_id_to_index(parent_id)
            if index is not None and index != self.current_section_index:
                self.set_active_section(index)
            self.load_photo_preview(item_id)
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

    def save_anomaly(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione a foto para associar uma anomalia.")
            return
        item_id = selected[0]
        if not self.find_photo_by_id(item_id):
            messagebox.showwarning("Atenção", "Selecione uma foto válida.")
            return
        photo = self.find_photo_by_id(item_id)
        if not photo:
            return
        anomaly_name = self.anomaly_var.get().strip()
        if not anomaly_name:
            messagebox.showwarning("Atenção", "Selecione uma anomalia antes de salvar.")
            return
        photo["anomaly"] = anomaly_name
        self.save_data()
        self.refresh_tree()
        self.tree.selection_set(item_id)
        self.set_last_action(f"Foto {photo['order']} - {anomaly_name}")

    def assign_selected_anomaly(self):
        if not self.tree.selection():
            return
        self.save_anomaly()

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
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        if not self.find_photo_by_id(item_id):
            messagebox.showwarning("Selecione uma foto para excluir.")
            return
        if not messagebox.askyesno("Excluir foto", "Deseja excluir esta foto?", parent=self.root):
            return
        if not self.current_cond:
            return
        photo = self.find_photo_by_id(item_id)
        photo_order = photo["order"] if photo else "?"
        for section in self.current_cond.get("sections", []):
            section["photos"] = [photo for photo in section["photos"] if photo["id"] != item_id]
        self.renumber_photos()
        self.save_data()
        self.refresh_tree()
        self.preview_label.config(image="", text="Selecione uma foto para ver o preview.")
        self.preview_image = None
        self.set_last_action(f"Foto {photo_order} excluída.")

    def move_photo(self, direction):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        if not self.find_photo_by_id(item_id):
            messagebox.showwarning("Selecione uma foto para mover.")
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

    def get_section_name_by_photo_id(self, photo_id):
        if not self.current_cond:
            return None
        for section in self.current_cond.get("sections", []):
            for photo in section.get("photos", []):
                if photo["id"] == photo_id:
                    return section.get("name", "")
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = RelatorioFotograficoApp(root)
    root.mainloop()
