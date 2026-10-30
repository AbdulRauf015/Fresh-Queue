"""FreshQueue - screens (frontend) of the grocery stock manager, written in Python (Tkinter).
All shop logic (the Queues, stock, FIFO sales, customer line, speed test) runs in the Java backend;
this program only shows the screens and sends the shopkeeper's clicks to the backend.
It offers 6 colour themes (2 dark) and 5 languages (3 written right-to-left)."""
import csv
import datetime
import glob
import json
import os
import shutil
import socket
import subprocess
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import themes
from api import Api, ApiError
from texts import LANGUAGES, RTL_LANGS, TEXTS, TYPES_EN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
BACKEND_OUT = os.path.join(BACKEND_DIR, "out")
SETTINGS_PATH = os.path.join(ROOT, "data", "settings.json")


# ---- colours: the active theme's colours live in these module-level names ---------------
def apply_theme(name):
    """Loads a theme: BG, CARD, ACCENT, PRIMARY, ... become module-level names used everywhere."""
    globals().update(themes.palette(name))


apply_theme("green")

# ---- right-to-left support -----------------------------------------------------------------
RTL = False  # set by App.build() according to the chosen language


def anc():
    """'Start of the line' anchor: west for left-to-right languages, east for right-to-left ones."""
    return "e" if RTL else "w"


def flip(anchor):
    return {"w": "e", "e": "w"}.get(anchor, anchor) if RTL else anchor


def side_start():
    return "right" if RTL else "left"


def side_end():
    return "left" if RTL else "right"


def gap(n):
    """Space after a widget that was packed from the start side."""
    return (0, n) if RTL else (n, 0)


def just():
    return "right" if RTL else "left"


_shaper = None


def shape(text):
    """Windows draws Arabic-script text correctly by itself. Linux/Mac Tk does not, so there we
    (optionally) use the arabic_reshaper + python-bidi packages when they are installed."""
    global _shaper
    if os.name == "nt":
        return text
    if _shaper is None:
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            _shaper = (arabic_reshaper.reshape, get_display)
        except Exception:
            _shaper = False
    if not _shaper:
        return text
    reshape, display = _shaper
    return "\n".join(display(reshape(line)) for line in text.split("\n"))


# ---- settings (language + theme are remembered) ----------------------------------------------
def load_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


# ---- fonts -----------------------------------------------------------------------------------
FONT = "Segoe UI"
FONT_CHOICES = ("Segoe UI", "Tahoma", "Calibri", "Helvetica Neue", "Arial", "Inter", "DejaVu Sans", "Helvetica")


def pick_font():
    """Use the first nice font that is really installed (Segoe UI on Windows - it also has Arabic letters)."""
    global FONT
    from tkinter import font as tkfont
    have = set(tkfont.families())
    for name in FONT_CHOICES:
        if name in have:
            FONT = name
            return


def font(size, weight="normal"):
    return (FONT, size, weight)


# ---- starting the Java backend -------------------------------------------
def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _hidden():
    return {"creationflags": 0x08000000} if os.name == "nt" else {}  # no black console window


LAST_ERROR = ""  # why the backend could not start (shown to the user)


def _tail(text, n=900):
    text = (text or "").strip()
    return text[-n:] if len(text) > n else text


def compile_backend():
    """Compiles the Java files into backend/out (only when something changed). Sets LAST_ERROR on failure."""
    global LAST_ERROR
    sources = glob.glob(os.path.join(BACKEND_DIR, "*.java"))
    if not sources:
        LAST_ERROR = "No Java files were found in the 'backend' folder."
        return False
    marker = os.path.join(BACKEND_OUT, "Server.class")
    if os.path.exists(marker) and os.path.getmtime(marker) >= max(os.path.getmtime(s) for s in sources):
        return True
    shutil.rmtree(BACKEND_OUT, ignore_errors=True)  # throw away old compiled files, start clean
    os.makedirs(BACKEND_OUT, exist_ok=True)
    try:
        r = subprocess.run(["javac", "-d", BACKEND_OUT] + sources, capture_output=True, text=True, **_hidden())
    except FileNotFoundError:
        LAST_ERROR = "The Java compiler 'javac' was not found. Install the JDK (not only the JRE) and add it to PATH."
        return False
    except OSError as e:
        LAST_ERROR = f"Could not run javac: {e}"
        return False
    if r.returncode != 0:
        LAST_ERROR = ("The Java files could not be compiled.\n"
                      "Tip: extract the zip into a NEW empty folder (do not copy it over an old version).\n\n"
                      + _tail(r.stdout + "\n" + r.stderr))
        return False
    return True


def start_backend():
    """Compiles (first time only) and starts the Java backend. Returns (process, api) or None."""
    global LAST_ERROR
    LAST_ERROR = ""
    if not compile_backend():
        return None
    log_path = os.path.join(ROOT, "data", "engine_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    port = free_port()
    try:
        log = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(["java", "-cp", BACKEND_OUT, "Server", str(port)], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT, **_hidden())
    except FileNotFoundError:
        LAST_ERROR = "The program 'java' was not found. Install Java (JDK) and add it to PATH."
        return None
    except OSError as e:
        LAST_ERROR = f"Could not start java: {e}"
        return None
    api = Api(port)
    for _ in range(75):  # wait up to ~15 seconds
        if proc.poll() is not None:
            log.flush()
            try:
                LAST_ERROR = "The engine stopped right after starting.\n\n" + _tail(open(log_path, encoding="utf-8").read())
            except OSError:
                LAST_ERROR = "The engine stopped right after starting."
            return None
        try:
            api.health()
            return proc, api
        except ApiError:
            time.sleep(0.2)
    proc.terminate()
    LAST_ERROR = "The engine did not answer within 15 seconds (a firewall or antivirus may be blocking it)."
    return None


# ---- small helpers -----------------------------------------------------
def make_button(parent, text, bg, hover, fg="white", command=None, size=12, padx=16, pady=10):
    b = tk.Button(parent, text=text, bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                  font=font(size, "bold"), relief="flat", bd=0, padx=padx, pady=pady,
                  cursor="hand2", command=command)
    b.bind("<Enter>", lambda e: b.configure(bg=hover))
    b.bind("<Leave>", lambda e: b.configure(bg=bg))
    return b


def fmt_money(v):
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"


def fmt_us(v):
    if v >= 100:
        return f"{v:,.0f}"
    if v >= 1:
        return f"{v:.1f}"
    return f"{v:.3f}"


def draw_boxes(c, entries, front_text, rear_text, empty_text="(empty)", bw=150, bh=56, gap_=38):
    """Draws a queue as boxes: FRONT on the left -> REAR on the right. entries = [(title, subtitle)]."""
    c.delete("all")
    c.configure(bg=CARD)
    x0, y0 = 14, 26
    x = x0
    n = len(entries)
    for i, (title, sub) in enumerate(entries):
        first = i == 0
        c.create_rectangle(x, y0, x + bw, y0 + bh, fill=PRIMARY_SOFT if first else BOX_BG,
                           outline=ACCENT if first else LINE, width=2 if first else 1)
        title = title if len(title) <= 17 else title[:16] + "..."
        c.create_text(x + 10, y0 + 17, text=title, anchor="w", font=font(11, "bold"), fill=TEXT)
        c.create_text(x + 10, y0 + 39, text=sub, anchor="w", font=font(9), fill=MUTED)
        if first:
            c.create_text(x, y0 - 12, text=front_text, anchor="w", font=font(9, "bold"), fill=ACCENT)
        if i == n - 1:
            c.create_text(x + bw, y0 - 12, text=rear_text, anchor="e", font=font(9, "bold"), fill=AMBER_TEXT)
        if i < n - 1:
            c.create_line(x + bw + 6, y0 + bh / 2, x + bw + gap_ - 6, y0 + bh / 2, arrow="last", fill=MUTED, width=2)
        x += bw + gap_
    if n == 0:
        c.create_text(x0, y0 + 24, text=empty_text, anchor="w", font=font(11), fill=MUTED)
    c.configure(scrollregion=(0, 0, x + 10, y0 + bh + 14))


def draw_chart(c, title, xs, series, xlabel):
    """Simple line chart. series = [(label, colour, [values...])], xs = list of queue sizes."""
    c.delete("all")
    c.configure(bg=CARD)
    w = max(c.winfo_width(), 320)
    h = max(c.winfo_height(), 200)
    left, right, top, bottom = 70, 36, 44, 46
    ymax = max(max(v) for _, _, v in series) * 1.15 or 1.0
    xmax = max(xs)
    c.create_text(left - 54, 14, text=title + "   (microseconds per operation)", anchor="w",
                  font=font(11, "bold"), fill=TEXT)
    for i in range(5):
        y = top + (h - top - bottom) * i / 4
        c.create_line(left, y, w - right, y, fill=LINE)
        c.create_text(left - 8, y, text=fmt_us(ymax * (1 - i / 4)), anchor="e", font=font(8), fill=MUTED)

    def px(n):
        return left + (w - left - right) * n / xmax

    def py(v):
        return top + (h - top - bottom) * (1 - v / ymax)

    for tick in range(0, xmax + 1, max(xmax // 4, 1)):
        c.create_text(px(tick), h - bottom + 14, text=f"{tick:,}", font=font(8), fill=MUTED)
    c.create_text((left + w - right) / 2, h - 10, text=xlabel, font=font(9), fill=MUTED)
    lx = left
    for label, colour, values in series:
        pts = []
        for n, v in zip(xs, values):
            pts += [px(n), py(v)]
        c.create_line(*pts, fill=colour, width=2.5)
        for i in range(0, len(pts), 2):
            c.create_oval(pts[i] - 3.5, pts[i + 1] - 3.5, pts[i] + 3.5, pts[i + 1] + 3.5, fill=colour, outline=colour)
        c.create_line(lx, 32, lx + 16, 32, fill=colour, width=3)
        t = c.create_text(lx + 22, 32, text=label, anchor="w", font=font(9), fill=TEXT)
        lx = c.bbox(t)[2] + 18


class ScrollFrame(tk.Frame):
    """A frame with a vertical scrollbar on its side; put widgets into .inner. Mouse wheel works too."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set, yscrollincrement=24)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        for w in (self.canvas, self.inner):
            w.bind("<Enter>", self._bind_wheel)
            w.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _e=None):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

    def _unbind_wheel(self, _e=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, e):
        step = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")


# ---- dialogs -------------------------------------------------------------
def _center(win, app):
    win.update_idletasks()
    x = app.winfo_rootx() + (app.winfo_width() - win.winfo_width()) // 2
    y = app.winfo_rooty() + max(20, (app.winfo_height() - win.winfo_height()) // 3)
    win.geometry(f"+{x}+{y}")


def _label(parent, text, size=11, fg=None, pady=(10, 3), **kw):
    lbl = tk.Label(parent, text=text, bg=CARD, fg=fg or MUTED, font=font(size), anchor=anc(), justify=just(), **kw)
    lbl.pack(fill="x", pady=pady)
    return lbl


def _entry(parent, label, value="", width=34):
    _label(parent, label)
    e = tk.Entry(parent, font=font(14), relief="flat", bg=FIELD_BG, fg=TEXT, width=width, justify=just(),
                 highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT, insertbackground=TEXT)
    e.insert(0, value)
    e.pack(fill="x", ipady=7)
    return e


def _dialog_shell(app, title_text):
    """Common window for the dialogs. Returns (window, inner frame)."""
    win = tk.Toplevel(app)
    win.title(title_text)
    win.configure(bg=BG)
    win.resizable(False, False)
    win.transient(app)
    card = tk.Frame(win, bg=CARD, highlightbackground=LINE, highlightthickness=1)
    card.pack(padx=22, pady=22)
    inner = tk.Frame(card, bg=CARD)
    inner.pack(padx=28, pady=24)
    tk.Label(inner, text=title_text, bg=CARD, fg=ACCENT, font=font(18, "bold"), anchor=anc()).pack(fill="x", pady=(0, 8))
    return win, inner


class ItemDialog:
    """Simple form to add a new item or edit an existing one."""

    def __init__(self, app, item=None):
        self.app = app
        app.dialog = self  # (lets tests / other code reach the open dialog)
        self.item = item
        t = app.t
        self.win, inner = _dialog_shell(app, t("edit_title") if item else t("add_title"))
        win = self.win

        self.name = _entry(inner, t("lbl_name"), item["name"] if item else "")
        _label(inner, t("lbl_type"))
        types = t("types")
        self.type = ttk.Combobox(inner, values=types, state="readonly", font=font(13), width=30, justify=just())
        if item and item["category"] in TYPES_EN:
            self.type.current(TYPES_EN.index(item["category"]))
        elif item:
            self.type.set(item["category"])
        else:
            self.type.current(0)
        self.type.pack(fill="x", ipady=5)
        self.qty = _entry(inner, t("lbl_qty"), str(item["quantity"]) if item else "")
        price = ""
        if item:
            price = str(int(item["price"])) if float(item["price"]).is_integer() else str(item["price"])
        self.price = _entry(inner, t("lbl_price"), price)

        _label(inner, t("lbl_exp"))
        row = tk.Frame(inner, bg=CARD)
        row.pack(fill="x")
        d = datetime.date.fromisoformat(item["expiry"]) if item else datetime.date.today() + datetime.timedelta(days=7)
        this_year = datetime.date.today().year
        months = t("months")
        parts = (("day", [str(i) for i in range(1, 32)], str(d.day), 5),
                 ("month", months, months[d.month - 1], 9),
                 ("year", [str(y) for y in range(this_year - 1, this_year + 8)], str(d.year), 7))
        boxes = {}
        for cap, values, current, width in parts:
            col = tk.Frame(row, bg=CARD)
            col.pack(side=side_start(), padx=gap(12))
            tk.Label(col, text=t(cap), bg=CARD, fg=MUTED, font=font(10), anchor=anc()).pack(fill="x")
            box = ttk.Combobox(col, values=values, state="readonly", width=width, font=font(13), justify=just())
            box.set(current)
            box.pack(ipady=5)
            boxes[cap] = box
        self.day, self.month, self.year = boxes["day"], boxes["month"], boxes["year"]

        self.msg = tk.Label(inner, text="", bg=CARD, fg=DANGER_TEXT, font=font(11, "bold"), wraplength=400,
                            justify=just(), anchor=anc())
        self.msg.pack(fill="x", pady=(12, 0))
        btns = tk.Frame(inner, bg=CARD)
        btns.pack(fill="x", pady=(14, 0))
        make_button(btns, t("save"), PRIMARY, PRIMARY_DARK, command=self.submit, padx=34).pack(side=side_start())
        make_button(btns, t("cancel"), NEUTRAL_BTN, NEUTRAL_HOVER, fg=TEXT, command=win.destroy,
                    padx=26).pack(side=side_start(), padx=gap(12))
        win.bind("<Return>", lambda e: self.submit())
        win.bind("<Escape>", lambda e: win.destroy())
        _center(win, app)
        win.grab_set()
        self.name.focus_set()

    def submit(self):
        months = self.app.t("months")
        month_no = months.index(self.month.get()) + 1
        idx = self.type.current()
        data = {
            "name": self.name.get().strip(),
            "category": TYPES_EN[idx] if idx >= 0 else self.type.get(),  # always stored in English
            "quantity": self.qty.get().strip(),
            "price": self.price.get().strip(),
            "expiry": f"{int(self.year.get()):04d}-{month_no:02d}-{int(self.day.get()):02d}",
        }
        try:
            resp = self.app.api.update(self.item["id"], data) if self.item else self.app.api.create(data)
        except ApiError as e:
            self.msg.configure(text=str(e))
            return
        self.win.destroy()
        self.app.after_change(resp, self.app.t("saved"))


class SaleDialog:
    """Record a sale: the backend takes the pieces from the OLDEST batches first (FIFO)."""

    def __init__(self, app, names, preselect=None):
        self.app = app
        app.dialog = self
        self.names = names
        t = app.t
        self.win, inner = _dialog_shell(app, t("sale_title"))
        win = self.win
        _label(inner, t("sale_note"), pady=(0, 6), wraplength=400)

        _label(inner, t("sale_item"))
        labels = [f"{n['name']}   ({n['available']})" for n in names]
        self.item = ttk.Combobox(inner, values=labels, state="readonly", font=font(13), width=34, justify=just())
        index = 0
        for i, n in enumerate(names):
            if preselect and n["name"] == preselect:
                index = i
        self.item.current(index)
        self.item.pack(fill="x", ipady=5)
        self.qty = _entry(inner, t("sale_qty"))

        self.msg = tk.Label(inner, text="", bg=CARD, fg=DANGER_TEXT, font=font(11, "bold"), wraplength=400,
                            justify=just(), anchor=anc())
        self.msg.pack(fill="x", pady=(12, 0))
        btns = tk.Frame(inner, bg=CARD)
        btns.pack(fill="x", pady=(14, 0))
        self.go = make_button(btns, t("sale_btn"), PRIMARY, PRIMARY_DARK, command=self.submit, padx=30)
        self.go.pack(side=side_start())
        self.cancel = make_button(btns, t("cancel"), NEUTRAL_BTN, NEUTRAL_HOVER, fg=TEXT, command=win.destroy, padx=26)
        self.cancel.pack(side=side_start(), padx=gap(12))
        win.bind("<Return>", lambda e: self.submit())
        win.bind("<Escape>", lambda e: win.destroy())
        _center(win, app)
        win.grab_set()
        self.qty.focus_set()

    def submit(self):
        if str(self.go["state"]) == "disabled":
            return
        t = self.app.t
        name = self.names[self.item.current()]["name"]
        try:
            r = self.app.api.sale(name, self.qty.get().strip())
        except ApiError as e:
            self.msg.configure(text=str(e), fg=DANGER_TEXT)
            return
        lines = [t("sale_done", q=r["quantity"], name=r["itemName"], amt=fmt_money(r["amount"]))]
        for p in r["parts"]:
            lines.append(t("sale_part", id=p["id"], took=p["took"], fin=t("sale_fin") if p["finished"] else ""))
        self.msg.configure(text="\n".join(lines), fg=ACCENT)
        self.go.configure(state="disabled")
        self.cancel.configure(text=t("close"))
        self.app.after_change(r, t("ok_done"))


# ---- main window ---------------------------------------------------------
class App(tk.Tk):
    def __init__(self, api, proc=None, settings=None):
        super().__init__()
        pick_font()
        settings = settings or {}
        self.api = api
        self.proc = proc
        self.lang = settings.get("lang") if settings.get("lang") in TEXTS else "en"
        self.theme = settings.get("theme") if settings.get("theme") in themes.BASE else themes.LIGHT_DEFAULT
        self.last_light = settings.get("last_light") if settings.get("last_light") in themes.BASE else themes.LIGHT_DEFAULT
        self.last_dark = settings.get("last_dark") if settings.get("last_dark") in themes.BASE else themes.DARK_DEFAULT
        if themes.is_dark(self.theme):
            self.last_dark = self.theme
        else:
            self.last_light = self.theme
        self.show_teacher = False
        self.tab_key = "stock"
        self.tabs = {}
        self.dialog = None
        self.log_lines = []
        self.line_last = ""
        self.stats = {}
        self.items = []
        self.queue = []
        self.bench = None
        self.flash_job = None
        self.search_var = tk.StringVar()

        self.title("FreshQueue - Stock Manager")
        w = min(1260, self.winfo_screenwidth() - 40)
        h = min(800, self.winfo_screenheight() - 90)
        self.geometry(f"{w}x{h}+10+10")
        self.minsize(960, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.build()
        self.refresh()

    # ------------------------------------------------------------ text
    def t(self, key, **kw):
        value = TEXTS[self.lang].get(key)
        if value is None:
            value = TEXTS["en"][key]  # words not translated yet fall back to English
        rtl = self.lang in RTL_LANGS
        if isinstance(value, list):
            return [shape(x) for x in value] if rtl else list(value)
        text = value.format(**kw) if kw else value
        return shape(text) if rtl else text

    def type_label(self, category):
        """Item types are stored in English; show them in the chosen language."""
        if category in TYPES_EN:
            return self.t("types")[TYPES_EN.index(category)]
        return category

    # ------------------------------------------------------------ styling
    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("Treeview", rowheight=44, font=font(13), background=CARD, fieldbackground=CARD,
                     foreground=TEXT, borderwidth=0)
        st.configure("Treeview.Heading", font=font(11, "bold"), background=HEAD_BG, foreground=MUTED,
                     relief="flat", padding=(10, 9))
        st.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
        st.map("Treeview.Heading", background=[("active", HEAD_BG)])
        st.configure("Compact.Treeview", rowheight=30, font=font(12), background=CARD, fieldbackground=CARD,
                     foreground=TEXT, borderwidth=0)
        st.configure("Compact.Treeview.Heading", font=font(11, "bold"), background=HEAD_BG, foreground=MUTED,
                     relief="flat", padding=(10, 7))
        st.map("Compact.Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
        st.configure("TCombobox", padding=4, fieldbackground=FIELD_BG, background=NEUTRAL_BTN, foreground=TEXT,
                     arrowcolor=TEXT, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        st.map("TCombobox", fieldbackground=[("readonly", FIELD_BG)], foreground=[("readonly", TEXT)],
               selectbackground=[("readonly", FIELD_BG)], selectforeground=[("readonly", TEXT)])
        st.configure("TScrollbar", background=NEUTRAL_BTN, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED,
                     lightcolor=NEUTRAL_BTN, darkcolor=NEUTRAL_BTN)
        st.map("TScrollbar", background=[("active", NEUTRAL_HOVER)])
        st.configure("TNotebook", background=BG, borderwidth=0, tabposition="ne" if RTL else "nw",
                     tabmargins=(0, 10, 24, 0) if RTL else (24, 10, 0, 0))
        st.configure("TNotebook.Tab", font=font(12, "bold"), padding=(24, 11), background=TAB_BG,
                     foreground=MUTED, borderwidth=0)
        st.map("TNotebook.Tab", background=[("selected", CARD)], foreground=[("selected", ACCENT)])
        self.option_add("*TCombobox*Listbox.font", font(13))
        self.option_add("*TCombobox*Listbox.background", FIELD_BG)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", SELECT)
        self.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    # ------------------------------------------------------------ building the screen
    def build(self):
        global RTL
        RTL = self.lang in RTL_LANGS
        apply_theme(self.theme)
        self._style()
        for w in self.winfo_children():
            w.destroy()
        self.configure(bg=BG)

        head = tk.Frame(self, bg=HEADER)
        head.pack(fill="x", side="top")
        left = tk.Frame(head, bg=HEADER)
        left.pack(side=side_start(), padx=26, pady=12)
        tk.Label(left, text="FreshQueue", bg=HEADER, fg="white", font=font(24, "bold"), anchor=anc()).pack(fill="x")
        tk.Label(left, text=self.t("app_sub"), bg=HEADER, fg=HEADER_SUB, font=font(12), anchor=anc()).pack(fill="x")
        right = tk.Frame(head, bg=HEADER)
        right.pack(side=side_end(), padx=22)
        make_button(right, self.t("teacher_hide") if self.show_teacher else self.t("teacher_show"),
                    HEADER_BTN, HEADER_HOVER, size=11, padx=14, pady=8,
                    command=self.toggle_teacher).pack(side=side_end(), padx=gap(10))
        self.header_menu(right, dict(LANGUAGES)[self.lang], [(c, n) for c, n in LANGUAGES], self.lang,
                         self.set_language, raw_labels=True).pack(side=side_end(), padx=gap(10))
        make_button(right, self.t("dark_off") if themes.is_dark(self.theme) else self.t("dark_on"),
                    HEADER_BTN, HEADER_HOVER, size=11, padx=14, pady=8,
                    command=self.toggle_dark).pack(side=side_end(), padx=gap(10))
        self.header_menu(right, self.t("settings_theme"),
                         [(n, self.t("th_" + n)) for n in themes.THEME_ORDER], self.theme,
                         self.set_theme).pack(side=side_end(), padx=gap(10))

        self.hint = tk.Label(self, text=self.t("hint"), bg=BG, fg=MUTED, font=font(11), anchor=anc(), justify=just())
        self.hint.pack(side="bottom", fill="x", padx=24, pady=(4, 10))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        order = [("stock", "tab_stock", self.build_stock_tab), ("line", "tab_line", self.build_line_tab),
                 ("hist", "tab_history", self.build_history_tab)]
        if self.show_teacher:
            order.append(("speed", "tab_speed", self.build_speed_tab))
        if RTL:
            order.reverse()
        self.tabs = {}
        for key, label, _builder in order:
            frame = tk.Frame(self.nb, bg=BG)
            self.tabs[key] = frame
            self.nb.add(frame, text=self.t(label))
        for key, _label_key, builder in order:
            builder(self.tabs[key])
        self.nb.select(self.tabs.get(self.tab_key, self.tabs["stock"]))

    def header_menu(self, parent, text, items, current, command, raw_labels=False):
        """A drop-down button in the top bar. items = [(code, label)]."""
        mb = tk.Menubutton(parent, text=shape(text) if (raw_labels and self.lang in RTL_LANGS) else text + "  v",
                           bg=HEADER_BTN, fg="white", activebackground=HEADER_HOVER, activeforeground="white",
                           font=font(11, "bold"), relief="flat", bd=0, padx=14, pady=8, cursor="hand2")
        if raw_labels:
            mb.configure(text=shape(text) + "  v")
        menu = tk.Menu(mb, tearoff=0, bg=CARD, fg=TEXT, activebackground=SELECT, activeforeground=TEXT, font=font(12))
        for code, label in items:
            mark = "●  " if code == current else "     "
            menu.add_command(label=mark + (shape(label) if raw_labels else label),
                             command=lambda c=code: command(c))
        mb["menu"] = menu
        return mb

    def stat_row(self, parent, defs):
        """Cards in a row; the first card is at the START of the line. Returns the value labels in order."""
        n = len(defs)
        labels = []
        for i, (key, color) in enumerate(defs):
            col = n - 1 - i if RTL else i
            card = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=0, column=col, sticky="ew", padx=(0, 12 if col < n - 1 else 0))
            parent.columnconfigure(col, weight=1)
            tk.Label(card, text=self.t(key).upper(), bg=CARD, fg=MUTED, font=font(10, "bold"), anchor=anc()).pack(
                fill="x", padx=18, pady=(10, 0))
            v = tk.Label(card, text="-", bg=CARD, fg=color, font=font(24, "bold"), anchor=anc())
            v.pack(fill="x", padx=18, pady=(0, 8))
            labels.append(v)
        return labels

    def table(self, parent, spec, height=None, style=None, **pack):
        """A Treeview with a scrollbar inside a card. spec = [(id, text, width, anchor, stretch)] in reading order."""
        frame = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        frame.pack(**pack)
        cols = [s[0] for s in spec]
        kw = {"height": height} if height else {}
        if style:
            kw["style"] = style
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse", **kw)
        for cid, text, width, anchor, stretch in spec:
            tree.heading(cid, text=text, anchor=flip(anchor))
            tree.column(cid, width=width, anchor=flip(anchor), stretch=stretch)
        if RTL:
            tree.configure(displaycolumns=list(reversed(cols)))
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=side_end(), fill="y")
        tree.pack(side=side_start(), fill="both", expand=True)
        tree.tag_configure("first", background=PRIMARY_SOFT)
        tree.tag_configure("soon", background=AMBER_SOFT)
        tree.tag_configure("bad", background=DANGER_SOFT)
        tree.tag_configure("odd", background=ODD_BG)
        return frame, tree

    def empty_box(self, frame):
        box = tk.Frame(frame, bg=CARD)
        title = tk.Label(box, text="", bg=CARD, fg=TEXT, font=font(17, "bold"), wraplength=700, justify="center")
        title.pack()
        sub = tk.Label(box, text="", bg=CARD, fg=MUTED, font=font(13), wraplength=700, justify="center")
        sub.pack(pady=(6, 12))
        return box, title, sub

    # ---------------------------------------------------------- stock tab
    def build_stock_tab(self, tab):
        self.alert = tk.Label(tab, text="", bg=AMBER_SOFT, fg=ALERT_FG, font=font(13, "bold"), anchor=anc(),
                              justify=just(), padx=18, pady=9)
        stats = tk.Frame(tab, bg=BG)
        self.stats_frame = stats
        stats.pack(fill="x", padx=24, pady=(14, 0))
        self.stat_labels = self.stat_row(stats, [("stat_items", ACCENT), ("stat_pieces", TEXT),
                                                 ("stat_soon", AMBER_TEXT), ("stat_low", DANGER_TEXT)])

        bar = tk.Frame(tab, bg=BG)
        bar.pack(fill="x", padx=24, pady=(12, 6))
        buttons = [
            (self.t("add"), PRIMARY, PRIMARY_DARK, "white", self.add_item),
            (self.t("sale"), BLUE, BLUE_DARK, "white", self.open_sale),
            (self.t("edit"), SOFT_BTN, SOFT_BTN_HOVER, SOFT_FG, self.edit_item),
            (self.t("remove"), DANGER, "#A2362E", "white", self.remove_item),
            (self.t("finished"), AMBER, "#C98A27", ON_AMBER, self.finish_oldest),
            (self.t("expired_btn"), NEUTRAL_BTN, NEUTRAL_HOVER, TEXT, self.remove_expired),
        ]
        for i, (text, bg, hover, fg, cmd) in enumerate(buttons):
            make_button(bar, text, bg, hover, fg=fg, command=cmd).pack(side=side_start(), padx=gap(8) if i else 0)

        srow = tk.Frame(tab, bg=BG)
        srow.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(srow, text=self.t("search"), bg=BG, fg=MUTED, font=font(12, "bold")).pack(
            side=side_start(), padx=gap(8))
        ent = tk.Entry(srow, textvariable=self.search_var, font=font(13), width=24, relief="flat", bg=FIELD_BG,
                       fg=TEXT, insertbackground=TEXT, justify=just(), highlightthickness=1,
                       highlightbackground=LINE, highlightcolor=ACCENT)
        ent.pack(side=side_start(), ipady=6)
        ent.bind("<KeyRelease>", lambda e: self.reload_stock())

        # teacher panel is packed before the table so the table takes what is left
        self.teacher = tk.Frame(tab, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        tk.Label(self.teacher, text=TEXTS["en"]["queue_title"], bg=CARD, fg=MUTED, font=font(9, "bold"),
                 anchor="w").pack(fill="x", padx=14, pady=(8, 2))
        cwrap = tk.Frame(self.teacher, bg=CARD)
        cwrap.pack(fill="x", padx=10)
        self.canvas = tk.Canvas(cwrap, height=100, bg=CARD, highlightthickness=0)
        hs = ttk.Scrollbar(cwrap, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=hs.set)
        self.canvas.pack(fill="x")
        hs.pack(fill="x")
        tk.Label(self.teacher, text=TEXTS["en"]["log_title"], bg=CARD, fg=MUTED, font=font(9, "bold"),
                 anchor="w").pack(fill="x", padx=14, pady=(6, 2))
        self.log = tk.Text(self.teacher, height=4, font=("Consolas", 10), bg=FIELD_BG, fg=TEXT, relief="flat",
                           wrap="word", padx=8, pady=6)
        self.log.pack(fill="x", padx=14, pady=(0, 10))
        for line in self.log_lines:
            self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        if self.show_teacher:
            self.teacher.pack(side="bottom", fill="x", padx=24, pady=(8, 0))

        spec = (("order", self.t("col_order"), 150, "w", False), ("name", self.t("col_name"), 240, "w", True),
                ("type", self.t("col_type"), 110, "w", False), ("qty", self.t("col_qty"), 90, "center", False),
                ("price", self.t("col_price"), 100, "e", False), ("exp", self.t("col_exp"), 130, "center", False),
                ("status", self.t("col_status"), 250, "w", True))
        self.table_frame, self.tree = self.table(tab, spec, fill="both", expand=True, padx=24, pady=(0, 6))
        self.tree.bind("<Double-1>", lambda e: self.edit_item())
        self.empty, self.empty_title, self.empty_hint = self.empty_box(self.table_frame)
        self.sample_btn = make_button(self.empty, self.t("sample"), SOFT_BTN, SOFT_BTN_HOVER, fg=SOFT_FG,
                                      command=self.load_sample)

    # ---------------------------------------------------------- customer line tab
    def build_line_tab(self, tab):
        cards = tk.Frame(tab, bg=BG)
        cards.pack(fill="x", padx=24, pady=(14, 0))
        weights = [3, 2, 4]
        for i, wgt in enumerate(weights):
            cards.columnconfigure(2 - i if RTL else i, weight=wgt)

        def put(i, widget):
            widget.grid(row=0, column=2 - i if RTL else i, sticky="nsew", padx=(0, 12 if i < 2 else 0))

        c1 = tk.Frame(cards, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        put(0, c1)
        tk.Label(c1, text=self.t("line_now"), bg=CARD, fg=MUTED, font=font(10, "bold"), anchor=anc()).pack(
            fill="x", padx=18, pady=(10, 0))
        self.serving_lbl = tk.Label(c1, text=self.t("line_none"), bg=CARD, fg=ACCENT, font=font(22, "bold"),
                                    anchor=anc())
        self.serving_lbl.pack(fill="x", padx=18, pady=(0, 8))
        make_button(c1, self.t("line_call"), PRIMARY, PRIMARY_DARK, command=self.call_next, size=13,
                    pady=11).pack(anchor=anc(), padx=18, pady=(0, 14))

        c2 = tk.Frame(cards, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        put(1, c2)
        tk.Label(c2, text=self.t("line_wait").upper(), bg=CARD, fg=MUTED, font=font(10, "bold"), anchor=anc()).pack(
            fill="x", padx=18, pady=(10, 0))
        self.waiting_lbl = tk.Label(c2, text="0", bg=CARD, fg=AMBER_TEXT, font=font(34, "bold"), anchor=anc())
        self.waiting_lbl.pack(fill="x", padx=18)

        c3 = tk.Frame(cards, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        put(2, c3)
        tk.Label(c3, text=self.t("line_name"), bg=CARD, fg=MUTED, font=font(11), anchor=anc(), justify=just()).pack(
            fill="x", padx=18, pady=(12, 3))
        self.cust_entry = tk.Entry(c3, font=font(14), relief="flat", bg=FIELD_BG, fg=TEXT, justify=just(),
                                   highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT,
                                   insertbackground=TEXT)
        self.cust_entry.pack(fill="x", padx=18, ipady=7)
        self.cust_entry.bind("<Return>", lambda e: self.join_line())
        make_button(c3, self.t("line_join"), BLUE, BLUE_DARK, command=self.join_line, size=13,
                    pady=11).pack(anchor=anc(), padx=18, pady=(10, 14))

        tk.Label(tab, text=self.t("line_strip"), bg=BG, fg=MUTED, font=font(10, "bold"), anchor=anc(),
                 justify=just()).pack(fill="x", padx=26, pady=(14, 2))
        sf = tk.Frame(tab, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        sf.pack(fill="x", padx=24)
        self.line_canvas = tk.Canvas(sf, height=104, bg=CARD, highlightthickness=0)
        hs = ttk.Scrollbar(sf, orient="horizontal", command=self.line_canvas.xview)
        self.line_canvas.configure(xscrollcommand=hs.set)
        self.line_canvas.pack(fill="x", padx=6)
        hs.pack(fill="x")

        self.line_last_lbl = tk.Label(tab, text="", bg=BG, fg=MUTED, font=("Consolas", 10), anchor="w", justify="left")
        if self.show_teacher:
            self.line_last_lbl.pack(fill="x", padx=26, pady=(6, 0))
            self.line_last_lbl.configure(text=self.line_last)

        spec = (("pos", self.t("col_pos"), 150, "w", False), ("token", self.t("col_token"), 100, "center", False),
                ("name", self.t("col_cname"), 300, "w", True), ("time", self.t("col_joined"), 130, "center", False))
        self.line_frame, self.line_tree = self.table(tab, spec, fill="both", expand=True, padx=24, pady=(10, 6))
        self.line_empty, self.line_empty_title, self.line_empty_sub = self.empty_box(self.line_frame)

    # ---------------------------------------------------------- sales history tab
    def build_history_tab(self, tab):
        stats = tk.Frame(tab, bg=BG)
        stats.pack(fill="x", padx=24, pady=(14, 0))
        self.hist_labels = self.stat_row(stats, [("hist_today", ACCENT), ("hist_pieces", TEXT), ("hist_count", MUTED)])
        self.hist_note = tk.Label(tab, text="", bg=BG, fg=MUTED, font=font(11), anchor=anc(), justify=just())
        self.hist_note.pack(fill="x", padx=26, pady=(10, 4))
        spec = (("time", self.t("col_time"), 170, "w", False), ("item", self.t("col_item"), 300, "w", True),
                ("qty", self.t("col_pieces"), 100, "center", False), ("amount", self.t("col_amount"), 150, "e", False))
        self.hist_frame, self.hist_tree = self.table(tab, spec, fill="both", expand=True, padx=24, pady=(0, 6))
        self.hist_empty, self.hist_empty_title, self.hist_empty_sub = self.empty_box(self.hist_frame)

    # ---------------------------------------------------------- speed test tab (teacher, English, left-to-right)
    def build_speed_tab(self, tab):
        global RTL
        saved, RTL = RTL, False  # this tab is a technical report page: always English, left to right
        try:
            self._build_speed(tab)
        finally:
            RTL = saved

    def _build_speed(self, tab):
        sf = ScrollFrame(tab)
        sf.pack(fill="both", expand=True)
        box = sf.inner
        tk.Label(box, text=self.t("speed_title"), bg=BG, fg=ACCENT, font=font(16, "bold"), anchor="w").pack(
            fill="x", padx=26, pady=(14, 2))
        self.speed_desc = tk.Label(box, text=self.t("speed_desc"), bg=BG, fg=MUTED, font=font(11), anchor="w",
                                   justify="left", wraplength=1000)
        self.speed_desc.pack(fill="x", padx=26)
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x", padx=24, pady=(10, 8))
        make_button(row, self.t("speed_run"), PRIMARY, PRIMARY_DARK, command=self.run_speed).pack(side="left")
        make_button(row, self.t("speed_save"), SOFT_BTN, SOFT_BTN_HOVER, fg=SOFT_FG,
                    command=self.save_speed).pack(side="left", padx=(10, 0))
        self.speed_status = tk.Label(row, text="", bg=BG, fg=AMBER_TEXT, font=font(11, "bold"))
        self.speed_status.pack(side="left", padx=14)

        spec = (("n", self.t("sp_n"), 110, "center", False), ("enq", self.t("sp_enq"), 130, "center", True),
                ("deq", self.t("sp_deq"), 150, "center", True), ("peek", self.t("sp_peek"), 140, "center", True),
                ("search", self.t("sp_search"), 120, "center", True), ("edit", self.t("sp_edit"), 120, "center", True),
                ("remove", self.t("sp_remove"), 130, "center", True))
        _f, self.speed_tree = self.table(box, spec, height=6, style="Compact.Treeview", fill="x", padx=24)

        charts = tk.Frame(box, bg=BG)
        charts.pack(fill="x", padx=24, pady=(12, 0))
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        self.chart_fast = tk.Canvas(charts, bg=CARD, highlightbackground=LINE, highlightthickness=1, height=300)
        self.chart_slow = tk.Canvas(charts, bg=CARD, highlightbackground=LINE, highlightthickness=1, height=300)
        self.chart_fast.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.chart_slow.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.chart_fast.bind("<Configure>", lambda e: self.draw_speed())
        self.chart_slow.bind("<Configure>", lambda e: self.draw_speed())
        self.conclusion = tk.Label(box, text=self.t("speed_empty"), bg=BG, fg=TEXT, font=font(11), anchor="w",
                                   justify="left", wraplength=1000)
        self.conclusion.pack(fill="x", padx=26, pady=(10, 20))
        self.speed_scroll = sf
        sf.canvas.bind("<Configure>", self._speed_resize, add="+")
        if self.bench:
            self.fill_speed()

    def _speed_resize(self, e):
        width = max(e.width - 80, 400)
        self.conclusion.configure(wraplength=width)
        self.speed_desc.configure(wraplength=width)

    # ------------------------------------------------------------ data -> screen
    def refresh(self):
        self.reload_stock()
        self.reload_line()
        self.reload_history()

    def _get(self, fn, *args):
        try:
            return fn(*args)
        except ApiError as e:
            messagebox.showerror("FreshQueue", str(e), parent=self)
            return None

    def reload_stock(self):
        q = self.search_var.get().strip()
        data = self._get(self.api.search, q) if q else self._get(self.api.items)
        if data is None:
            return
        self.items, self.stats, self.queue = data["items"], data["stats"], data["queue"]
        self.render_stock()

    def status_of(self, it):
        d = it["daysLeft"]
        if d < 0:
            return self.t("expired"), "bad"
        if d == 0:
            text, tag = self.t("today"), "bad"
        elif d == 1:
            text, tag = self.t("soon1"), "soon"
        elif d <= 7:
            text, tag = self.t("soon", d=d), "soon"
        else:
            text, tag = self.t("fresh"), ""
        if it["low"]:
            text += self.t("low_suffix")
            tag = tag or "soon"
        return text, tag

    def render_stock(self):
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        position = {q["id"]: i + 1 for i, q in enumerate(self.queue)}
        for n, it in enumerate(self.items):
            pos = position.get(it["id"], 0)
            status, tag = self.status_of(it)
            tags = [tag] if tag else (["first"] if pos == 1 else (["odd"] if n % 2 else []))
            self.tree.insert("", "end", iid=str(it["id"]), tags=tags, values=(
                self.t("first") if pos == 1 else str(pos), it["name"], self.type_label(it["category"]),
                it["quantity"], fmt_money(it["price"]), it["expiry"], status))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])

        st = self.stats
        self.stat_labels[0].configure(text=str(st.get("batches", 0)))
        self.stat_labels[1].configure(text=f"{st.get('units', 0):,}")
        self.stat_labels[2].configure(text=str(st.get("expiringSoon", 0)))
        self.stat_labels[3].configure(text=str(st.get("lowStock", 0)))

        msgs = []
        if st.get("expired", 0):
            msgs.append(self.t("alert_exp", n=st["expired"]))
        if st.get("expiringSoon", 0):
            msgs.append(self.t("alert_soon", n=st["expiringSoon"]))
        if st.get("lowStock", 0):
            msgs.append(self.t("alert_low", n=st["lowStock"]))
        if msgs:
            bad = st.get("expired", 0) > 0
            self.alert.configure(text="!   " + "     |     ".join(msgs), bg=DANGER_SOFT if bad else AMBER_SOFT,
                                 fg=DANGER_TEXT if bad else ALERT_FG)
            if not self.alert.winfo_ismapped():
                self.alert.pack(fill="x", padx=24, pady=(14, 0), before=self.stats_frame)
        else:
            self.alert.pack_forget()

        if not self.items:
            if st.get("batches", 0) == 0:
                self.empty_title.configure(text=self.t("empty_title"))
                self.empty_hint.configure(text=self.t("empty_hint"))
                self.sample_btn.pack()
            else:
                self.empty_title.configure(text=self.t("no_match"))
                self.empty_hint.configure(text="")
                self.sample_btn.pack_forget()
            self.empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty.place_forget()
        draw_boxes(self.canvas, [(q["name"], f"ID {q['id']}  |  Qty {q['quantity']}") for q in self.queue],
                   self.t("front"), self.t("rear"), "(empty)")

    def reload_line(self):
        data = self._get(self.api.line)
        if data is None:
            return
        self.line_tree.delete(*self.line_tree.get_children())
        for i, c in enumerate(data["line"]):
            self.line_tree.insert("", "end", tags=["first"] if i == 0 else (["odd"] if i % 2 else []), values=(
                self.t("line_front") if i == 0 else str(i + 1), f"#{c['token']}", c["name"], c["time"]))
        s = data["serving"]
        self.serving_lbl.configure(text=f"#{s['token']}  {s['name']}" if s else self.t("line_none"))
        self.waiting_lbl.configure(text=str(data["waiting"]))
        draw_boxes(self.line_canvas, [(c["name"], f"Token #{c['token']}  |  {c['time']}") for c in data["line"]],
                   TEXTS["en"]["line_front"], self.t("rear"), "(empty)")
        if data["waiting"] == 0:
            self.line_empty_title.configure(text=self.t("line_empty"))
            self.line_empty_sub.configure(text="")
            self.line_empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.line_empty.place_forget()

    def reload_history(self):
        data = self._get(self.api.history)
        if data is None:
            return
        self.hist_tree.delete(*self.hist_tree.get_children())
        for i, r in enumerate(reversed(data["sales"])):  # newest first
            self.hist_tree.insert("", "end", tags=["odd"] if i % 2 else [], values=(
                r["time"], r["item"], r["quantity"], fmt_money(r["amount"])))
        self.hist_labels[0].configure(text=fmt_money(data["todayAmount"]))
        self.hist_labels[1].configure(text=f"{data['todayPieces']:,}")
        self.hist_labels[2].configure(text=f"{data['kept']} / {data['capacity']}")
        self.hist_note.configure(text=self.t("hist_note", cap=data["capacity"]))
        if data["kept"] == 0:
            self.hist_empty_title.configure(text=self.t("hist_empty"))
            self.hist_empty_sub.configure(text="")
            self.hist_empty.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.hist_empty.place_forget()

    # ------------------------------------------------------------ stock actions
    def selected_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("FreshQueue", self.t("select_first"), parent=self)
            return None
        return next((i for i in self.items if i["id"] == int(sel[0])), None)

    def add_item(self):
        ItemDialog(self)

    def edit_item(self):
        item = self.selected_item()
        if item:
            ItemDialog(self, item)

    def remove_item(self):
        item = self.selected_item()
        if item and messagebox.askyesno("FreshQueue", self.t("remove_q", name=item["name"]), parent=self):
            self.run(lambda: self.api.delete(item["id"]), self.t("removed"))

    def finish_oldest(self):
        if not self.queue:
            messagebox.showinfo("FreshQueue", self.t("empty_stock"), parent=self)
            return
        name = self.queue[0]["name"]
        if messagebox.askyesno("FreshQueue", self.t("finished_q", name=name), parent=self):
            self.run(self.api.sell_first, self.t("ok_done"))

    def remove_expired(self):
        n = self.stats.get("expired", 0)
        if n == 0:
            messagebox.showinfo("FreshQueue", self.t("no_expired"), parent=self)
            return
        if messagebox.askyesno("FreshQueue", self.t("expired_q", n=n), parent=self):
            self.run(self.api.remove_expired, self.t("removed"))

    def open_sale(self):
        names = self._get(self.api.stock_names)
        if names is None:
            return
        if not names:
            messagebox.showinfo("FreshQueue", self.t("no_names"), parent=self)
            return
        sel = self.tree.selection()
        pre = None
        if sel:
            it = next((i for i in self.items if i["id"] == int(sel[0])), None)
            pre = it["name"] if it else None
        SaleDialog(self, names, pre)

    def load_sample(self):
        self.run(self.api.load_sample, self.t("ok_done"))

    # ------------------------------------------------------------ line actions
    def join_line(self):
        name = self.cust_entry.get().strip()
        self.cust_entry.delete(0, "end")
        self.run(lambda: self.api.join_line(name), self.t("ok_done"))
        self.cust_entry.focus_set()

    def call_next(self):
        self.run(self.api.call_next, self.t("ok_done"), info=True)

    # ------------------------------------------------------------ speed test
    def run_speed(self):
        self.speed_status.configure(text=self.t("speed_running"))
        self.config(cursor="watch")
        self.update()
        try:
            self.bench = self.api.benchmark()["results"]
        except ApiError as e:
            messagebox.showerror("FreshQueue", str(e), parent=self)
            self.bench = None
        self.config(cursor="")
        self.speed_status.configure(text="")
        if self.bench:
            self.fill_speed()

    def fill_speed(self):
        self.speed_tree.delete(*self.speed_tree.get_children())
        for i, r in enumerate(self.bench):
            self.speed_tree.insert("", "end", tags=["odd"] if i % 2 else [], values=(
                f"{r['n']:,}", fmt_us(r["enqueue"]), fmt_us(r["dequeue"]), fmt_us(r["peek"]),
                fmt_us(r["search"]), fmt_us(r["edit"]), fmt_us(r["remove"])))
        self.draw_speed()
        a, z = self.bench[0], self.bench[-1]
        grow_n = z["n"] / a["n"]
        grow_t = z["search"] / a["search"]
        ratio = z["search"] / max(z["enqueue"], 1e-9)
        self.conclusion.configure(text=(
            f"Result: with {z['n']:,} items, adding one item takes about {fmt_us(z['enqueue'])} us and taking the first "
            f"item about {fmt_us(z['dequeue'])} us. They stay almost the same however big the queue is (O(1)).\n"
            f"Searching for one item takes about {fmt_us(z['search'])} us (editing {fmt_us(z['edit'])} us, removing a "
            f"chosen item {fmt_us(z['remove'])} us). When the queue became {grow_n:,.0f} times bigger, search became "
            f"about {grow_t:,.0f} times slower (O(n)), and it is about {ratio:,.0f} times slower than adding.\n"
            f"Conclusion: a Queue is excellent when items only join at the REAR and leave from the FRONT (FIFO), but it is "
            f"a poor choice when you must reach items in the middle."))

    def draw_speed(self):
        if not self.bench or not hasattr(self, "chart_fast"):
            return
        xs = [r["n"] for r in self.bench]
        draw_chart(self.chart_fast, TEXTS["en"]["speed_fast"], xs, [
            ("Add (enqueue)", ACCENT, [r["enqueue"] for r in self.bench]),
            ("Remove first (dequeue)", AMBER_TEXT, [r["dequeue"] for r in self.bench]),
            ("Peek", CH_PURPLE, [r["peek"] for r in self.bench])], TEXTS["en"]["speed_x"])
        draw_chart(self.chart_slow, TEXTS["en"]["speed_slow"], xs, [
            ("Search", DANGER_TEXT, [r["search"] for r in self.bench]),
            ("Edit", CH_PURPLE, [r["edit"] for r in self.bench]),
            ("Remove chosen", CH_TEAL, [r["remove"] for r in self.bench])], TEXTS["en"]["speed_x"])

    def save_speed(self):
        if not self.bench:
            messagebox.showinfo("FreshQueue", self.t("speed_empty"), parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="speed_test.csv",
                                            filetypes=[("CSV file", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["items_in_queue", "enqueue_us", "dequeue_us", "peek_us", "search_us", "edit_us", "remove_us"])
            for r in self.bench:
                w.writerow([r["n"], r["enqueue"], r["dequeue"], r["peek"], r["search"], r["edit"], r["remove"]])
        self.flash(self.t("saved"))

    # ------------------------------------------------------------ shared plumbing
    def run(self, call, ok_text, info=False):
        try:
            resp = call()
        except ApiError as e:
            (messagebox.showinfo if info else messagebox.showerror)("FreshQueue", str(e), parent=self)
            return
        self.after_change(resp, ok_text)

    def after_change(self, resp, ok_text):
        self.add_log(resp)
        self.refresh()
        self.flash(resp.get("message") or ok_text)

    def add_log(self, resp):
        line = (f"[{time.strftime('%H:%M:%S')}] {resp.get('op', '')}: {resp.get('detail', '')}\n"
                f"   -> used {resp.get('enq', 0)} enqueue + {resp.get('deq', 0)} dequeue calls")
        self.log_lines.append(line)
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        if str(resp.get("op", "")).startswith("LINE"):
            self.line_last = (f"{TEXTS['en']['line_last']} {resp.get('detail', '')}  "
                              f"({resp.get('enq', 0)} enqueue + {resp.get('deq', 0)} dequeue)")
            self.line_last_lbl.configure(text=self.line_last)

    def flash(self, text):
        self.hint.configure(text="  " + text, fg=ACCENT, font=font(12, "bold"))
        if self.flash_job:
            self.after_cancel(self.flash_job)
        self.flash_job = self.after(3500, lambda: self.hint.configure(text=self.t("hint"), fg=MUTED, font=font(11)))

    # ------------------------------------------------------------ settings: language, theme, dark mode
    def remember_tab(self):
        try:
            current = str(self.nb.select())
        except tk.TclError:
            return
        for key, frame in self.tabs.items():
            if str(frame) == current:
                self.tab_key = key

    def save(self):
        save_settings({"lang": self.lang, "theme": self.theme, "last_light": self.last_light,
                       "last_dark": self.last_dark})

    def _rebuild(self):
        self.remember_tab()
        self.build()
        self.refresh()
        self.save()

    def set_language(self, code):
        if code in TEXTS and code != self.lang:
            self.lang = code
            self._rebuild()

    def set_theme(self, name):
        if name in themes.BASE and name != self.theme:
            self.theme = name
            if themes.is_dark(name):
                self.last_dark = name
            else:
                self.last_light = name
            self._rebuild()

    def toggle_dark(self):
        self.set_theme(self.last_light if themes.is_dark(self.theme) else self.last_dark)

    def toggle_teacher(self):
        self.show_teacher = not self.show_teacher
        self._rebuild()

    def on_close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.destroy()


def report_problem(reason):
    """Show the real reason and also save it in data/startup_error.txt so it can be sent for help."""
    try:
        os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
        with open(os.path.join(ROOT, "data", "startup_error.txt"), "w", encoding="utf-8") as f:
            f.write(reason)
    except OSError:
        pass
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("FreshQueue", TEXTS["en"]["backend_fail"] + "\n\n" + TEXTS["ro"]["backend_fail"]
                         + "\n\n---- Reason ----\n" + (reason or "unknown"))


def main():
    try:
        result = start_backend()
        if result is None:
            report_problem(LAST_ERROR)
            return
        proc, api = result
        App(api, proc, load_settings()).mainloop()
    except Exception:  # never fail silently (pythonw has no console)
        import traceback
        report_problem(traceback.format_exc())


if __name__ == "__main__":
    main()
