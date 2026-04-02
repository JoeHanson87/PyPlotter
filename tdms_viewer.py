"""
TDMS Data Viewer
A dark-mode application for viewing and comparing TDMS data files.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from nptdms import TdmsFile

# ── Dark-mode colour palette ───────────────────────────────────────────────
DARK_BG      = "#1e1e2e"
DARKER_BG    = "#181825"
PANEL_BG     = "#24273a"
ACCENT       = "#89b4fa"
TEXT_FG      = "#cdd6f4"
SUBTEXT_FG   = "#a6adc8"
BORDER       = "#313244"
HIGHLIGHT_BG = "#313244"
BUTTON_BG    = "#313244"
BUTTON_ACTIVE= "#45475a"
ERROR_FG     = "#f38ba8"
SUCCESS_FG   = "#a6e3a1"

# Matplotlib line colours cycled over multiple files/channels
PLOT_COLORS  = [
    "#89b4fa", "#a6e3a1", "#fab387", "#f38ba8",
    "#cba6f7", "#89dceb", "#f9e2af", "#74c7ec",
]

# ── Helpers ────────────────────────────────────────────────────────────────

def _configure_ttk_style():
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(".",
                    background=DARK_BG, foreground=TEXT_FG,
                    fieldbackground=PANEL_BG, bordercolor=BORDER,
                    troughcolor=DARKER_BG, font=("Segoe UI", 10))

    style.configure("TFrame", background=DARK_BG)
    style.configure("Panel.TFrame", background=PANEL_BG)

    style.configure("TLabel", background=DARK_BG, foreground=TEXT_FG)
    style.configure("Sub.TLabel", background=PANEL_BG, foreground=SUBTEXT_FG, font=("Segoe UI", 9))
    style.configure("Header.TLabel", background=PANEL_BG, foreground=ACCENT,
                    font=("Segoe UI", 10, "bold"))

    style.configure("TButton",
                    background=BUTTON_BG, foreground=TEXT_FG,
                    borderwidth=1, relief="flat", padding=(8, 4))
    style.map("TButton",
              background=[("active", BUTTON_ACTIVE), ("pressed", BORDER)],
              relief=[("pressed", "sunken")])

    style.configure("Accent.TButton",
                    background=ACCENT, foreground=DARKER_BG,
                    borderwidth=0, relief="flat", padding=(8, 4),
                    font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", "#74c7ec"), ("pressed", "#6ab0e0")])

    style.configure("Treeview",
                    background=PANEL_BG, foreground=TEXT_FG,
                    fieldbackground=PANEL_BG, borderwidth=0,
                    rowheight=22)
    style.map("Treeview",
              background=[("selected", HIGHLIGHT_BG)],
              foreground=[("selected", ACCENT)])
    style.configure("Treeview.Heading",
                    background=DARKER_BG, foreground=ACCENT,
                    borderwidth=0)

    style.configure("TScrollbar",
                    background=PANEL_BG, troughcolor=DARKER_BG,
                    arrowcolor=TEXT_FG, borderwidth=0)

    style.configure("TSeparator", background=BORDER)


# ── Tooltip helper ─────────────────────────────────────────────────────────

class _ToolTip:
    """Simple hover tooltip for tkinter widgets."""

    def __init__(self, widget: tk.Widget, text: str):
        self._widget = widget
        self._text   = text
        self._tw: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 4
        y = self._widget.winfo_rooty()
        self._tw = tk.Toplevel(self._widget)
        self._tw.wm_overrideredirect(True)
        self._tw.wm_geometry(f"+{x}+{y}")
        tk.Label(self._tw, text=self._text,
                 bg=PANEL_BG, fg=TEXT_FG,
                 relief="flat", borderwidth=1,
                 font=("Segoe UI", 9),
                 padx=6, pady=3).pack()

    def _hide(self, _event=None):
        if self._tw:
            self._tw.destroy()
            self._tw = None


# ── Channel selection item ─────────────────────────────────────────────────

class ChannelItem:
    """Holds state for a single channel check-box row in the sidebar."""

    def __init__(self, file_id: int, file_label: str, group: str, channel: str,
                 color: str, var: tk.BooleanVar):
        self.file_id    = file_id
        self.file_label = file_label
        self.group      = group
        self.channel    = channel
        self.color      = color
        self.var        = var          # BooleanVar – checked = plotted


# ── Main application ───────────────────────────────────────────────────────

class TdmsViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PyPlotter – TDMS Viewer")
        self.geometry("1300x800")
        self.minsize(900, 600)
        self.configure(bg=DARK_BG)

        _configure_ttk_style()

        # State
        self._files: dict[int, dict] = {}   # file_id -> {path, label, TdmsFile}
        self._file_counter = 0
        self._channel_items: list[ChannelItem] = []
        self._color_index = 0

        self._build_menu()
        self._build_layout()

    # ── Menu bar ──────────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self, bg=DARKER_BG, fg=TEXT_FG,
                          activebackground=HIGHLIGHT_BG, activeforeground=ACCENT,
                          relief="flat", borderwidth=0)

        file_menu = tk.Menu(menubar, tearoff=False,
                            bg=DARKER_BG, fg=TEXT_FG,
                            activebackground=HIGHLIGHT_BG, activeforeground=ACCENT)
        file_menu.add_command(label="Open TDMS File(s)…", command=self._open_files,
                              accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Clear All Files",   command=self._clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",              command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=False,
                            bg=DARKER_BG, fg=TEXT_FG,
                            activebackground=HIGHLIGHT_BG, activeforeground=ACCENT)
        view_menu.add_command(label="Select All Channels",   command=self._select_all)
        view_menu.add_command(label="Deselect All Channels", command=self._deselect_all)
        view_menu.add_separator()
        view_menu.add_command(label="Reset Zoom",            command=self._reset_zoom)
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=False,
                            bg=DARKER_BG, fg=TEXT_FG,
                            activebackground=HIGHLIGHT_BG, activeforeground=ACCENT)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)
        self.bind_all("<Control-o>", lambda _e: self._open_files())

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Root paned window (sidebar | plot area)
        self._paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Left sidebar ──────────────────────────────────────────────────
        self._sidebar = ttk.Frame(self._paned, style="Panel.TFrame", width=280)
        self._sidebar.pack_propagate(False)
        self._paned.add(self._sidebar, weight=0)

        ttk.Label(self._sidebar, text="  Channels", style="Header.TLabel",
                  padding=(0, 8, 0, 4)).pack(fill=tk.X)
        ttk.Separator(self._sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8)

        # Buttons row
        btn_frame = ttk.Frame(self._sidebar, style="Panel.TFrame")
        btn_frame.pack(fill=tk.X, padx=8, pady=(6, 4))
        ttk.Button(btn_frame, text="Open File",
                   command=self._open_files,
                   style="Accent.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Clear All",
                   command=self._clear_all).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Channel list with scroll
        list_container = ttk.Frame(self._sidebar, style="Panel.TFrame")
        list_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._canvas_sidebar = tk.Canvas(list_container,
                                         bg=PANEL_BG, highlightthickness=0,
                                         bd=0)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL,
                                  command=self._canvas_sidebar.yview)
        self._channel_frame = ttk.Frame(self._canvas_sidebar, style="Panel.TFrame")

        self._channel_frame.bind(
            "<Configure>",
            lambda e: self._canvas_sidebar.configure(
                scrollregion=self._canvas_sidebar.bbox("all")
            )
        )

        self._canvas_sidebar.create_window((0, 0), window=self._channel_frame, anchor="nw")
        self._canvas_sidebar.configure(yscrollcommand=scrollbar.set)

        self._canvas_sidebar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse-wheel scroll on sidebar
        self._canvas_sidebar.bind("<Enter>",  self._bind_mousewheel)
        self._canvas_sidebar.bind("<Leave>",  self._unbind_mousewheel)

        # Empty-state label
        self._empty_label = ttk.Label(
            self._channel_frame,
            text="Open a TDMS file\nto get started.",
            style="Sub.TLabel",
            justify="center"
        )
        self._empty_label.pack(pady=20)

        # ── Right plot area ───────────────────────────────────────────────
        plot_frame = ttk.Frame(self._paned, style="TFrame")
        self._paned.add(plot_frame, weight=1)

        self._fig = Figure(facecolor=DARKER_BG, edgecolor=BORDER)
        self._ax  = self._fig.add_subplot(111)
        self._style_axes()

        self._canvas_plot = FigureCanvasTkAgg(self._fig, master=plot_frame)
        self._canvas_plot.draw()
        self._canvas_plot.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Navigation toolbar (dark-styled)
        toolbar_frame = tk.Frame(plot_frame, bg=DARKER_BG)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self._canvas_plot, toolbar_frame)
        toolbar.config(bg=DARKER_BG)
        for widget in toolbar.winfo_children():
            try:
                widget.config(bg=DARKER_BG, fg=TEXT_FG)
            except tk.TclError:
                pass
        toolbar.update()

        # Status bar
        self._status_var = tk.StringVar(value="Ready – open a TDMS file to begin.")
        status_bar = tk.Label(self, textvariable=self._status_var,
                              bg=DARKER_BG, fg=SUBTEXT_FG,
                              anchor="w", padx=8, pady=3,
                              font=("Segoe UI", 9))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ── Axis / plot styling ───────────────────────────────────────────────

    def _style_axes(self):
        ax = self._ax
        ax.set_facecolor(DARK_BG)
        ax.tick_params(colors=SUBTEXT_FG, which="both")
        ax.xaxis.label.set_color(TEXT_FG)
        ax.yaxis.label.set_color(TEXT_FG)
        ax.title.set_color(TEXT_FG)
        ax.spines[:].set_color(BORDER)
        ax.grid(True, color=BORDER, linestyle="--", linewidth=0.6, alpha=0.8)
        self._fig.tight_layout(pad=1.5)

    # ── Mouse-wheel binding for sidebar ──────────────────────────────────

    def _bind_mousewheel(self, _event):
        self._canvas_sidebar.bind_all("<MouseWheel>",  self._on_mousewheel)
        self._canvas_sidebar.bind_all("<Button-4>",    self._on_mousewheel)
        self._canvas_sidebar.bind_all("<Button-5>",    self._on_mousewheel)

    def _unbind_mousewheel(self, _event):
        self._canvas_sidebar.unbind_all("<MouseWheel>")
        self._canvas_sidebar.unbind_all("<Button-4>")
        self._canvas_sidebar.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = int(-event.delta / 120)
        self._canvas_sidebar.yview_scroll(delta, "units")

    # ── File I/O ──────────────────────────────────────────────────────────

    def _open_files(self):
        paths = filedialog.askopenfilenames(
            title="Open TDMS File(s)",
            filetypes=[("TDMS files", "*.tdms"), ("All files", "*.*")]
        )
        for path in paths:
            self._load_file(path)

    def _load_file(self, path: str):
        # Avoid loading the same file twice
        for fd in self._files.values():
            if os.path.abspath(fd["path"]) == os.path.abspath(path):
                messagebox.showinfo("Already Loaded",
                                    f"'{os.path.basename(path)}' is already loaded.")
                return

        try:
            tdms_file = TdmsFile.read(path)
        except Exception as exc:
            messagebox.showerror("Load Error",
                                 f"Could not load '{os.path.basename(path)}':\n{exc}")
            return

        self._file_counter += 1
        file_id    = self._file_counter
        file_label = os.path.basename(path)

        self._files[file_id] = {
            "path":  path,
            "label": file_label,
            "tdms":  tdms_file,
        }

        self._populate_channels(file_id, file_label, tdms_file)
        self._status_var.set(f"Loaded: {file_label}")

    def _populate_channels(self, file_id: int, file_label: str, tdms_file: TdmsFile):
        # Remove empty-state label once we have data
        if self._empty_label.winfo_exists():
            self._empty_label.destroy()

        # File header row
        file_header = ttk.Frame(self._channel_frame, style="Panel.TFrame")
        file_header.pack(fill=tk.X, padx=4, pady=(10, 2))
        file_header.file_id = file_id  # tag for later removal

        ttk.Label(file_header,
                  text=f"[TDMS] {file_label}",
                  style="Header.TLabel",
                  wraplength=220).pack(side=tk.LEFT, fill=tk.X, expand=True)

        close_btn = ttk.Button(file_header, text="X", width=3,
                               command=lambda fid=file_id: self._remove_file(fid))
        close_btn.pack(side=tk.RIGHT)
        # Tooltip for accessibility
        _ToolTip(close_btn, f"Close {file_label}")

        ttk.Separator(self._channel_frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, padx=8, pady=(0, 4))

        for group in tdms_file.groups():
            for channel in group.channels():
                data = channel[:]
                if data is None or len(data) == 0:
                    continue

                color = PLOT_COLORS[self._color_index % len(PLOT_COLORS)]
                self._color_index += 1

                var = tk.BooleanVar(value=False)
                item = ChannelItem(
                    file_id=file_id,
                    file_label=file_label,
                    group=group.name,
                    channel=channel.name,
                    color=color,
                    var=var,
                )
                self._channel_items.append(item)

                row = ttk.Frame(self._channel_frame, style="Panel.TFrame")
                row.pack(fill=tk.X, padx=8, pady=1)
                row.item_ref = item  # back-reference

                # Colour swatch
                swatch = tk.Label(row, bg=color, width=2, relief="flat")
                swatch.pack(side=tk.LEFT, padx=(0, 4))

                cb = tk.Checkbutton(
                    row,
                    variable=var,
                    command=self._refresh_plot,
                    bg=PANEL_BG, fg=TEXT_FG,
                    activebackground=PANEL_BG, activeforeground=ACCENT,
                    selectcolor=BORDER,
                    relief="flat", bd=0,
                    cursor="hand2",
                )
                cb.pack(side=tk.LEFT)

                label_text = f"{group.name} / {channel.name}"
                ttk.Label(row, text=label_text, style="Sub.TLabel",
                          wraplength=160).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._canvas_sidebar.update_idletasks()
        self._canvas_sidebar.configure(
            scrollregion=self._canvas_sidebar.bbox("all")
        )

    # ── File removal ─────────────────────────────────────────────────────

    def _remove_file(self, file_id: int):
        if file_id not in self._files:
            return

        # Remove channel items for this file
        self._channel_items = [ci for ci in self._channel_items
                               if ci.file_id != file_id]

        # Remove UI rows
        for widget in self._channel_frame.winfo_children():
            fid = getattr(widget, "file_id", None)
            ref = getattr(widget, "item_ref", None)
            if fid == file_id or (ref is not None and ref.file_id == file_id):
                widget.destroy()

        del self._files[file_id]

        if not self._files:
            # Show empty state again
            self._empty_label = ttk.Label(
                self._channel_frame,
                text="Open a TDMS file\nto get started.",
                style="Sub.TLabel",
                justify="center"
            )
            self._empty_label.pack(pady=20)

        self._refresh_plot()
        self._status_var.set(
            f"Removed file. {len(self._files)} file(s) loaded."
        )

    # ── Plot refresh ──────────────────────────────────────────────────────

    def _refresh_plot(self):
        self._ax.cla()
        self._style_axes()

        plotted = 0
        for item in self._channel_items:
            if not item.var.get():
                continue
            fd = self._files.get(item.file_id)
            if fd is None:
                continue

            tdms_file = fd["tdms"]
            try:
                channel = tdms_file[item.group][item.channel]
                data    = channel[:]
                if data is None or len(data) == 0:
                    continue

                # Use time track if available, otherwise use sample index
                try:
                    t = channel.time_track()
                except Exception:
                    t = np.arange(len(data))

                label = f"{item.file_label} – {item.group}/{item.channel}"
                self._ax.plot(t, data, color=item.color, linewidth=1.2,
                              label=label, alpha=0.9)
                plotted += 1
            except Exception as exc:
                print(f"[warn] Could not plot {item.group}/{item.channel}: {exc}")

        if plotted > 0:
            legend = self._ax.legend(
                fontsize=8,
                facecolor=PANEL_BG,
                edgecolor=BORDER,
                labelcolor=TEXT_FG,
                loc="upper right",
            )
            legend.get_frame().set_alpha(0.9)

        self._ax.set_xlabel("Time / Sample Index", color=TEXT_FG)
        self._ax.set_ylabel("Value", color=TEXT_FG)
        self._ax.set_title("TDMS Channel Overlay", color=TEXT_FG)

        self._canvas_plot.draw()
        self._status_var.set(
            f"{plotted} channel(s) plotted  •  {len(self._files)} file(s) loaded."
        )

    # ── Convenience actions ───────────────────────────────────────────────

    def _select_all(self):
        for item in self._channel_items:
            item.var.set(True)
        self._refresh_plot()

    def _deselect_all(self):
        for item in self._channel_items:
            item.var.set(False)
        self._refresh_plot()

    def _clear_all(self):
        file_ids = list(self._files.keys())
        for fid in file_ids:
            self._remove_file(fid)

    def _reset_zoom(self):
        self._ax.autoscale()
        self._canvas_plot.draw()

    def _show_about(self):
        messagebox.showinfo(
            "About PyPlotter",
            "PyPlotter – TDMS Viewer\n\n"
            "Open and overlay multiple TDMS data files for visual comparison.\n\n"
            "Libraries: nptdms · matplotlib · numpy · tkinter"
        )


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    app = TdmsViewer()
    app.mainloop()


if __name__ == "__main__":
    main()
