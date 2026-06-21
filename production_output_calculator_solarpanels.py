import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter, MaxNLocator

# MAIN WINDOW
root = tk.Tk()
root.title("PRODUCTION OUTPUT CALCULATOR")
root.geometry("1280x820")
root.minsize(1180, 760)

style = ttk.Style(root)

df = None
current_fig = None
loaded_file_name = ""
current_fig = None
current_choice = ""   # remembers which graph is currently shown

# REQUIRED COLUMNS
stage_columns = [
    "Wafers_Produced", "Textured_Cells", "Anti_Reflective_Coated",
    "PN_Junction_Formed", "Contact_Printed", "Interconnections",
    "Encapsulated", "Junction_Box_Attached", "Test passed"]
ALL_GRAPH_OPTIONS = [
    "Total Output",
    "Mean Output",
    "Daily Test Passed",
    "Daily Efficiency",
    "Cost vs Selling",
    "Overall Efficiency"]
# THEMES
THEMES = {
    "light": {
        "bg": "#f5f6fa",
        "panel": "#ffffff",
        "sidebar": "#ffffff",
        "card": "#ffffff",
        "text": "#2f3640",
        "muted": "#718093",
        "border": "#dcdde1",
        "btn_green": "#27ae60",
        "btn_blue": "#2980b9",
    },
    "dark": {
        "bg": "#151a1f",
        "panel": "#1e272e",
        "sidebar": "#1e272e",
        "card": "#1b232a",
        "text": "#f5f6fa",
        "muted": "#a4b0be",
        "border": "#2f3640",
        "btn_green": "#27ae60",
        "btn_blue": "#2980b9",
    }
}
current_theme = "light"

def theme():
    return THEMES[current_theme]
# CARD CREATOR
def make_card(parent, title, value="N/A"):
    c = tk.Frame(parent, bd=0, highlightthickness=1)
    t = tk.Label(c, text=title, font=("Segoe UI", 10, "bold"), anchor="w")
    v = tk.Label(c, text=value, font=("Segoe UI", 18, "bold"), anchor="w")
    t.pack(fill="x", padx=12, pady=(10, 0))
    v.pack(fill="x", padx=12, pady=(0, 10))
    return c, t, v

# HELPERS
def _num_series(col_name: str):
    if df is None or col_name not in df.columns:
        return None
    return pd.to_numeric(df[col_name], errors="coerce")

def fmt(x):
    if x is None:
        return "N/A"
    try:
        if pd.isna(x):
            return "N/A"
    except Exception:
        pass
    try:
        if abs(x - round(x)) < 1e-9:
            return f"{int(round(x)):,}"
    except Exception:
        pass
    try:
        return f"{x:,.2f}"
    except Exception:
        return str(x)

def _fmt_commas(x, pos=None):
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)

def _finalize_axes(ax):
    ax.relim()
    ax.autoscale_view()
    ax.margins(y=0.18)
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_commas))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))

def _wrap_stage_label(name: str) -> str:
    """
    Makes long stage names visible by wrapping them into 2 lines.
    Example: Anti_Reflective_Coated -> Anti Reflective\nCoated
    """
    s = name.replace("_", " ")
    parts = s.split(" ")
    if len(parts) <= 2:
        return s
    mid = len(parts) // 2
    return " ".join(parts[:mid]) + "\n" + " ".join(parts[mid:])

# CSV PREVIEW
def clear_preview():
    for w in preview_table_frame.winfo_children():
        w.destroy()

def show_preview(dataframe: pd.DataFrame, max_rows: int = 12, max_cols: int = 15):
    clear_preview()

    if dataframe is None or dataframe.empty:
        tk.Label(preview_table_frame, text="No data to preview", font=("Segoe UI", 11)).pack(pady=10)
        apply_theme()
        return

    cols = list(dataframe.columns)[:max_cols]
    preview_df = dataframe[cols].head(max_rows).copy()

    tree = ttk.Treeview(preview_table_frame, columns=cols, show="headings", height=max_rows)
    vsb = ttk.Scrollbar(preview_table_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(preview_table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=140, anchor="center")

    for _, row in preview_df.iterrows():
        tree.insert("", "end", values=[row[c] for c in cols])

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    preview_table_frame.grid_rowconfigure(0, weight=1)
    preview_table_frame.grid_columnconfigure(0, weight=1)

# VALIDATION
def compute_available_graphs(cols_set: set) -> list:
    available = []

    if all(c in cols_set for c in stage_columns):
        available += ["Total Output", "Mean Output"]

    if "Day" in cols_set and "Test passed" in cols_set:
        available.append("Daily Test Passed")

    if "Day" in cols_set and "Eff" in cols_set:
        available.append("Daily Efficiency")

    if "Day" in cols_set and "Real cost price" in cols_set and "Selling price" in cols_set:
        available.append("Cost vs Selling")

    if "Wafers_Produced" in cols_set and "Test passed" in cols_set:
        available.append("Overall Efficiency")

    return available

def show_upload_instructions():
    msg = (
        "UPLOAD INSTRUCTIONS\n\n"
        "✅ Use ONLY the solar panel production CSV (.csv)\n"
        "✅ Column names must match EXACTLY (case + spaces)\n"
        "✅ Avoid empty cells in numeric columns\n"
        "✅ Numeric columns should be numbers only (avoid %, commas, text)\n\n"
        "Stage columns (for Total/Mean Output):\n"
        "Wafers_Produced, Textured_Cells, Anti_Reflective_Coated,\n"
        "PN_Junction_Formed, Contact_Printed, Interconnections,\n"
        "Encapsulated, Junction_Box_Attached, Test passed\n\n"
        "Extra columns:\n"
        "Daily Test Passed → Day + Test passed\n"
        "Daily Efficiency → Day + Eff\n"
        "Cost vs Selling → Day + Real cost price + Selling price\n"
        "Overall Efficiency → Wafers_Produced + Test passed\n\n"
        "Tip: After upload, dropdown shows ONLY graphs possible from your CSV."
    )
    messagebox.showinfo("CSV Upload Instructions", msg)

def show_validation_popup(cols_set: set):
    available = compute_available_graphs(cols_set)

    missing_stage = [c for c in stage_columns if c not in cols_set]
    missing_daily_test = [c for c in ["Day", "Test passed"] if c not in cols_set]
    missing_daily_eff = [c for c in ["Day", "Eff"] if c not in cols_set]
    missing_cost = [c for c in ["Day", "Real cost price", "Selling price"] if c not in cols_set]
    missing_overall = [c for c in ["Wafers_Produced", "Test passed"] if c not in cols_set]

    lines = []
    lines.append("CSV loaded. Column check result:\n")
    lines.append("Graphs enabled:")
    if available:
        for g in available:
            lines.append(f"• {g}")
    else:
        lines.append("• None (required columns missing)")

    lines.append("\nMissing columns (if you want these graphs):")
    lines.append("• Total/Mean Output needs ALL stage columns:")
    lines.append("  " + ("None" if not missing_stage else ", ".join(missing_stage)))
    lines.append("• Daily Test Passed needs Day, Test passed:")
    lines.append("  " + ("None" if not missing_daily_test else ", ".join(missing_daily_test)))
    lines.append("• Daily Efficiency needs Day, Eff:")
    lines.append("  " + ("None" if not missing_daily_eff else ", ".join(missing_daily_eff)))
    lines.append("• Cost vs Selling needs Day, Real cost price, Selling price:")
    lines.append("  " + ("None" if not missing_cost else ", ".join(missing_cost)))
    lines.append("• Overall Efficiency needs Wafers_Produced, Test passed:")
    lines.append("  " + ("None" if not missing_overall else ", ".join(missing_overall)))

    messagebox.showinfo("CSV Validation", "\n".join(lines))
    
# DASHBOARD UPDATE
def update_dashboard():
    wafers = _num_series("Wafers_Produced")
    passed = _num_series("Test passed")
    eff = _num_series("Eff")
    cost = _num_series("Real cost price")
    sell = _num_series("Selling price")

    total_wafers = wafers.sum() if wafers is not None else None
    total_passed = passed.sum() if passed is not None else None

    overall_eff = None
    if wafers is not None and passed is not None:
        denom = wafers.sum()
        overall_eff = (passed.sum() / denom) * 100 if denom and denom != 0 else 0

    avg_eff = eff.mean() if eff is not None else None
    avg_cost = cost.mean() if cost is not None else None
    avg_sell = sell.mean() if sell is not None else None
    avg_profit = (sell - cost).mean() if cost is not None and sell is not None else None

    best_day = None
    best_val = None
    if df is not None and "Day" in df.columns and "Test passed" in df.columns:
        tmp = df[["Day", "Test passed"]].copy()
        tmp["Test passed"] = pd.to_numeric(tmp["Test passed"], errors="coerce")
        idx = tmp["Test passed"].idxmax()
        if pd.notna(idx):
            best_day = tmp.loc[idx, "Day"]
            best_val = tmp.loc[idx, "Test passed"]

    card_total_wafers_value.config(text=fmt(total_wafers))
    card_total_passed_value.config(text=fmt(total_passed))
    card_overall_eff_value.config(text=("N/A" if overall_eff is None else f"{overall_eff:.2f}%"))
    card_avg_eff_value.config(text=("N/A" if avg_eff is None else f"{avg_eff:.2f}"))
    card_avg_profit_value.config(text=fmt(avg_profit))

# PERFECT PNG SAVE
def save_graph():
    global current_fig
    if current_fig is None:
        messagebox.showwarning("No Graph", "Generate a graph first, then click Save Graph.")
        return

    default_name = "graph.png"
    if loaded_file_name:
        base = os.path.splitext(loaded_file_name)[0]
        default_name = f"{base}_graph.png"

    file_path = filedialog.asksaveasfilename(
        title="Save Graph As",
        defaultextension=".png",
        initialfile=default_name,
        filetypes=[("PNG Image", "*.png")]
    )
    if not file_path:
        return

    try:
        current_fig.savefig(file_path, dpi=300, bbox_inches="tight", pad_inches=0.25)
        messagebox.showinfo("Saved", f"Graph saved successfully ✅\n\n{file_path}")
    except Exception as e:
        messagebox.showerror("Save Failed", f"Could not save graph:\n{e}")

# FIGURE BUILDER
def build_figure(choice: str, figsize=(11.2, 6.8)):
    fig, ax = plt.subplots(figsize=figsize)
    if choice in ("Total Output", "Mean Output"):
        labels = [_wrap_stage_label(c) for c in stage_columns]
        x = list(range(len(stage_columns)))

        if choice == "Total Output":
            vals = [pd.to_numeric(df[col], errors="coerce").sum() for col in stage_columns]
            bars = ax.bar(x, vals)
            ax.set_title("Total Output Per Stage", fontsize=16)
            for i, v in enumerate(vals):
                ax.text(i, v, f"{int(v):,}", ha="center", va="bottom", fontsize=9)
        else:
            vals = [pd.to_numeric(df[col], errors="coerce").mean() for col in stage_columns]
            bars = ax.bar(x, vals)
            ax.set_title("Mean Output Per Stage", fontsize=16)
            for i, v in enumerate(vals):
                ax.text(i, v, f"{v:,.2f}", ha="center", va="bottom", fontsize=9)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right") 
        _finalize_axes(ax)
        fig.subplots_adjust(bottom=0.28)

    elif choice == "Daily Test Passed":
        x = df["Day"]
        y = pd.to_numeric(df["Test passed"], errors="coerce")
        ax.bar(x, y)
        ax.plot(x, y)
        ax.set_title("Daily Test Passed", fontsize=16)
        _finalize_axes(ax)
        fig.tight_layout(pad=1.2)

    elif choice == "Daily Efficiency":
        x = df["Day"]
        y = pd.to_numeric(df["Eff"], errors="coerce")
        ax.bar(x, y)
        ax.plot(x, y)
        ax.set_title("Daily Efficiency", fontsize=16)
        _finalize_axes(ax)
        fig.tight_layout(pad=1.2)

    elif choice == "Cost vs Selling":
        xlabels = df["Day"].tolist()
        x = list(range(len(xlabels)))
        width = 0.4
        cost = pd.to_numeric(df["Real cost price"], errors="coerce")
        sell = pd.to_numeric(df["Selling price"], errors="coerce")

        ax.bar([i - width/2 for i in x], cost, width, label="Cost")
        ax.bar([i + width/2 for i in x], sell, width, label="Selling")

        ax.set_xticks(x)
        ax.set_xticklabels(xlabels)
        ax.legend()
        ax.set_title("Cost vs Selling Price", fontsize=16)
        _finalize_axes(ax)
        fig.tight_layout(pad=1.2)

    elif choice == "Overall Efficiency":
        wafers = pd.to_numeric(df["Wafers_Produced"], errors="coerce").sum()
        passed = pd.to_numeric(df["Test passed"], errors="coerce").sum()
        efficiency = (passed / wafers) * 100 if wafers else 0
        ax.text(0.5, 0.5, f"Overall Efficiency\n{efficiency:.2f}%",
                fontsize=30, ha='center', va='center')
        ax.axis("off")
        fig.tight_layout(pad=1.2)

    return fig

# FULLSCREEN GRAPH WINDOW
def open_fullscreen_graph(_event=None):
    if df is None:
        messagebox.showwarning("Warning", "Load CSV first!")
        return
    if not current_choice:
        messagebox.showwarning("Warning", "Select a graph first!")
        return

    win = tk.Toplevel(root)
    win.title(f"FULLSCREEN GRAPH - {current_choice}")

    try:
        win.state("zoomed")
    except Exception:
        win.attributes("-fullscreen", True)

    def exit_fullscreen(event=None):
        try:
            win.attributes("-fullscreen", False)
        except Exception:
            pass
        win.destroy()

    win.bind("<Escape>", exit_fullscreen)

    topbar = tk.Frame(win)
    topbar.pack(fill="x")

    lbl = tk.Label(topbar, text=f"Graph: {current_choice}  (Press Esc to close)",
                   font=("Segoe UI", 11, "bold"))
    lbl.pack(side="left", padx=12, pady=8)

    close_btn = tk.Button(topbar, text="Close (Esc)", command=exit_fullscreen,
                          font=("Segoe UI", 10, "bold"), padx=10, pady=6)
    close_btn.pack(side="right", padx=12, pady=8)

    holder = tk.Frame(win)
    holder.pack(fill="both", expand=True)

    plt.close("all")
    fig = build_figure(current_choice, figsize=(14, 8))

    canvas = FigureCanvasTkAgg(fig, master=holder)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
# FULLSCREEN CSV VIEWER
def open_fullscreen_csv(event=None):
    if df is None:
        messagebox.showwarning("Warning", "Load CSV first!")
        return

    win = tk.Toplevel(root)
    win.title("FULLSCREEN CSV VIEW")

    try:
        win.state("zoomed")
    except:
        win.attributes("-fullscreen", True)

    def exit_full(event=None):
        try:
            win.attributes("-fullscreen", False)
        except:
            pass
        win.destroy()

    win.bind("<Escape>", exit_full)

    th = theme()
    win.configure(bg=th["bg"])

    # Top bar
    top = tk.Frame(win, bg=th["bg"])
    top.pack(fill="x")

    lbl = tk.Label(
        top,
        text=f"CSV Preview  (Press Esc to close)",
        font=("Segoe UI", 11, "bold"),
        bg=th["bg"],
        fg=th["text"]
    )
    lbl.pack(side="left", padx=12, pady=8)

    close_btn = tk.Button(
        top,
        text="Close (Esc)",
        font=("Segoe UI", 10, "bold"),
        command=exit_full,
        padx=10,
        pady=6
    )
    close_btn.pack(side="right", padx=12, pady=8)

    # Table container
    frame = tk.Frame(win, bg=th["bg"])
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    cols = list(df.columns)

    tree = ttk.Treeview(frame, columns=cols, show="headings")
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=140, anchor="center")

    for _, row in df.iterrows():
        tree.insert("", "end", values=list(row))

    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

# LOAD CSV
def load_csv():
    global df, loaded_file_name, current_fig, current_choice

    show_upload_instructions()

    file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV Files", "*.csv")]
    )
    if not file_path:
        return

    try:
        df = pd.read_csv(file_path)
        df.columns = [c.strip() for c in df.columns]
        loaded_file_name = os.path.basename(file_path)

        cols_set = set(df.columns)
        available = compute_available_graphs(cols_set)

        dropdown.config(values=available)
        if available:
            dropdown.config(state="readonly")
            graph_choice.set("")
        else:
            dropdown.config(state="disabled")
            graph_choice.set("")

        show_validation_popup(cols_set)

        status_label.config(text=f"CSV Loaded ✅ | Rows: {len(df)}")

        show_preview(df)
        update_dashboard()

        current_choice = ""
        current_fig = None
        for widget in graph_frame.winfo_children():
            widget.destroy()

        apply_theme()

    except Exception as e:
        df = None
        loaded_file_name = ""
        current_fig = None
        current_choice = ""
        dropdown.config(state="disabled", values=ALL_GRAPH_OPTIONS)
        graph_choice.set("")
        status_label.config(text="Failed to load CSV ❌")
        messagebox.showerror("Error", f"Failed to load file:\n{e}")
        update_dashboard()
        clear_preview()
        for widget in graph_frame.winfo_children():
            widget.destroy()
        apply_theme()

def show_graph(event=None):
    global current_fig, current_choice

    if df is None:
        messagebox.showwarning("Warning", "Load CSV first!")
        return

    choice = graph_choice.get()
    if not choice:
        return

    current_choice = choice

    plt.close("all")

    for widget in graph_frame.winfo_children():
        widget.destroy()

    try:
        fig = build_figure(choice, figsize=(11.2, 6.8))
        current_fig = fig

        #fullscreen button + graph
        container = tk.Frame(graph_frame, bg=theme()["bg"])
        container.pack(fill="both", expand=True)

        top_bar = tk.Frame(container, bg=theme()["bg"])
        top_bar.pack(fill="x")

        fs_btn = tk.Button(
            top_bar,
            text="⛶ Fullscreen",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=4,
            command=open_fullscreen_graph
        )
        fs_btn.pack(side="right", padx=10, pady=6)

        graph_holder = tk.Frame(container, bg=theme()["bg"])
        graph_holder.pack(fill="both", expand=True)

        canvas = FigureCanvasTkAgg(fig, master=graph_holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    except Exception as e:
        current_fig = None
        messagebox.showerror("Error", f"Something went wrong while plotting:\n{e}")

# THEME
def apply_theme():
    th = theme()

    root.configure(bg=th["bg"])
    title_label.config(bg=th["bg"], fg=th["text"])
    subtitle_label.config(bg=th["bg"], fg=th["muted"])

    upload_btn.config(bg=th["btn_green"], fg="white", activebackground=th["btn_green"])
    theme_btn.config(bg=th["btn_blue"], fg="white", activebackground=th["btn_blue"])

    status_label.config(bg=th["bg"], fg=th["muted"])

    for card, title_lbl, value_lbl in metric_cards:
        card.config(bg=th["card"], highlightbackground=th["border"])
        title_lbl.config(bg=th["card"], fg=th["muted"])
        value_lbl.config(bg=th["card"], fg=th["text"])

    style.configure("TCombobox", padding=6)

def toggle_theme():
    global current_theme
    current_theme = "dark" if current_theme == "light" else "light"
    apply_theme()

# BUILD UI 

root.configure(bg=THEMES["light"]["bg"])

title_label = tk.Label(root, text="PRODUCTION OUTPUT CALCULATOR",
                       font=("Segoe UI", 30, "bold"), bg=THEMES["light"]["bg"])
title_label.pack(pady=(25, 6))

subtitle_label = tk.Label(root, text="Solar Panel Production • Simple Analytics Dashboard",
                          font=("Segoe UI", 12), bg=THEMES["light"]["bg"])
subtitle_label.pack(pady=(0, 18))

btn_frame = tk.Frame(root, bg=THEMES["light"]["bg"])
btn_frame.pack(pady=(0, 18))

upload_btn = tk.Button(btn_frame, text="Upload CSV File", font=("Segoe UI", 12, "bold"),
                       padx=22, pady=10, command=load_csv)
upload_btn.pack(side="left", padx=10)

theme_btn = tk.Button(btn_frame, text="Toggle Theme", font=("Segoe UI", 12, "bold"),
                      padx=22, pady=10, command=toggle_theme)
theme_btn.pack(side="left", padx=10)

select_label = tk.Label(root, text="SELECT PARAMETER",
                        font=("Segoe UI", 16, "bold"), bg=THEMES["light"]["bg"])
select_label.pack(pady=(0, 10))

graph_choice = tk.StringVar()
dropdown = ttk.Combobox(root, textvariable=graph_choice, state="disabled",
                        width=38, font=("Segoe UI", 12), values=ALL_GRAPH_OPTIONS)
dropdown.pack(pady=(0, 10))
dropdown.bind("<<ComboboxSelected>>", show_graph)

status_label = tk.Label(root, text="Please load CSV file",
                        font=("Segoe UI", 11), bg=THEMES["light"]["bg"])
status_label.pack(pady=(0, 12))

# Summary cards (static)
cards_row = tk.Frame(root, bg=THEMES["light"]["bg"])
cards_row.pack(pady=(0, 12))

metric_cards = []

card_total_wafers, t1, card_total_wafers_value = make_card(cards_row, "Total Wafers")
card_total_passed, t2, card_total_passed_value = make_card(cards_row, "Total Test Passed")
card_overall_eff, t3, card_overall_eff_value = make_card(cards_row, "Overall Efficiency")
card_avg_eff, t4, card_avg_eff_value = make_card(cards_row, "Avg Daily Efficiency")
card_avg_profit, t5, card_avg_profit_value = make_card(cards_row, "Avg Profit / Day")

for c in (card_total_wafers, card_total_passed, card_overall_eff, card_avg_eff, card_avg_profit):
    c.pack(side="left", padx=10)

metric_cards += [
    (card_total_wafers, t1, card_total_wafers_value),
    (card_total_passed, t2, card_total_passed_value),
    (card_overall_eff, t3, card_overall_eff_value),
    (card_avg_eff, t4, card_avg_eff_value),
    (card_avg_profit, t5, card_avg_profit_value),
]

# Graph area
graph_container = tk.Frame(root, bg=THEMES["light"]["bg"])
graph_container.pack(fill="both", expand=True, padx=30, pady=(0, 10))

graph_frame = tk.Frame(graph_container, bg=THEMES["light"]["bg"])
graph_frame.pack(fill="both", expand=True)

# Make graph area fullscreen on click
graph_frame.bind("<Button-1>", open_fullscreen_graph)

# CSV preview
preview_panel = tk.Frame(root, bg=THEMES["light"]["bg"])
preview_panel.pack(fill="x", padx=30, pady=(0, 20))
# Fullscreen CSV button
csv_btn = tk.Button(
    preview_panel,
    text="⛶ Fullscreen CSV",
    font=("Segoe UI", 10, "bold"),
    command=open_fullscreen_csv
)
csv_btn.pack(anchor="e", pady=(0, 6))

preview_table_frame = tk.Frame(preview_panel, bg=THEMES["light"]["bg"])
preview_table_frame.pack(fill="x")

# Save button (optional in this layout)
save_btn = tk.Button(root, text="Save Graph (PNG)", font=("Segoe UI", 11, "bold"),
                     padx=18, pady=8, command=save_graph)
save_btn.pack(pady=(0, 16))

# Init
update_dashboard()
apply_theme()

root.mainloop()
