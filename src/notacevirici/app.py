"""Nota Çevirici: arayüz (tkinter) ve komut satırı girişi."""
from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
from pathlib import Path

from .omr import find_audiveris
from .pipeline import convert_file

APP_NAME = "Nota Çevirici"


def _config_file() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "NotaCevirici" / "config.json"


def load_config() -> dict:
    try:
        return json.loads(_config_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    try:
        f = _config_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(cfg), encoding="utf-8")
    except Exception:
        pass


def run_cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Keman anahtarını alto anahtarına çevirir.")
    ap.add_argument("girdi", help="PDF, JPEG/PNG veya MusicXML dosyası")
    ap.add_argument("-o", "--cikti", help="Çıktı PDF yolu")
    args = ap.parse_args(argv)
    src = Path(args.girdi)
    out = Path(args.cikti) if args.cikti else src.with_name(src.stem + "_alto.pdf")
    exe = find_audiveris(load_config().get("audiveris"))
    try:
        convert_file(src, out, exe, print)
        return 0
    except Exception as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 1


def run_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    cfg = load_config()
    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("640x460")

    src_var = tk.StringVar()
    out_var = tk.StringVar()
    aud_var = tk.StringVar(value=find_audiveris(cfg.get("audiveris")) or "")
    msgs: queue.Queue = queue.Queue()

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(1, weight=1)

    def pick_src():
        p = filedialog.askopenfilename(
            title="Nota dosyasını seçin",
            filetypes=[("Nota dosyaları", "*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.mxl *.musicxml *.xml"),
                       ("Tüm dosyalar", "*.*")])
        if p:
            src_var.set(p)
            out_var.set(str(Path(p).with_name(Path(p).stem + "_alto.pdf")))

    def pick_out():
        p = filedialog.asksaveasfilename(title="PDF'i kaydet", defaultextension=".pdf",
                                         filetypes=[("PDF", "*.pdf")])
        if p:
            out_var.set(p)

    def pick_aud():
        p = filedialog.askopenfilename(title="Audiveris.exe konumunu seçin",
                                       filetypes=[("Audiveris", "Audiveris.exe"), ("Exe", "*.exe")])
        if p:
            aud_var.set(p)
            cfg["audiveris"] = p
            save_config(cfg)

    ttk.Label(frm, text="Nota dosyası (PDF/JPEG):").grid(row=0, column=0, sticky="w", pady=4)
    ttk.Entry(frm, textvariable=src_var).grid(row=0, column=1, sticky="ew", padx=6)
    ttk.Button(frm, text="Seç...", command=pick_src).grid(row=0, column=2)

    ttk.Label(frm, text="Çıktı PDF:").grid(row=1, column=0, sticky="w", pady=4)
    ttk.Entry(frm, textvariable=out_var).grid(row=1, column=1, sticky="ew", padx=6)
    ttk.Button(frm, text="Seç...", command=pick_out).grid(row=1, column=2)

    ttk.Label(frm, text="Audiveris:").grid(row=2, column=0, sticky="w", pady=4)
    ttk.Entry(frm, textvariable=aud_var).grid(row=2, column=1, sticky="ew", padx=6)
    ttk.Button(frm, text="Seç...", command=pick_aud).grid(row=2, column=2)

    ttk.Label(
        frm, foreground="#555",
        text="Keman anahtarı → Alto anahtarı (nota isimleri aynı, bir oktav aşağı yazılır)",
    ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 8))

    btn = ttk.Button(frm, text="Çevir")
    btn.grid(row=4, column=0, columnspan=3, sticky="ew", pady=4)

    log_box = tk.Text(frm, height=14, state="disabled", wrap="word")
    log_box.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
    frm.rowconfigure(5, weight=1)

    def log(text: str):
        msgs.put(("log", text))

    def append(text: str):
        log_box.configure(state="normal")
        log_box.insert("end", text + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def worker(src: Path, out: Path, exe: str | None):
        try:
            results = convert_file(src, out, exe, log)
            msgs.put(("done", "\n".join(str(r) for r in results)))
        except Exception as e:
            msgs.put(("error", str(e)))

    def start():
        if not src_var.get() or not out_var.get():
            messagebox.showwarning(APP_NAME, "Lütfen nota dosyasını ve çıktı yolunu belirleyin.")
            return
        btn.configure(state="disabled")
        append("İşlem başladı...")
        exe = aud_var.get() or None
        threading.Thread(target=worker, args=(Path(src_var.get()), Path(out_var.get()), exe),
                         daemon=True).start()

    def poll():
        try:
            while True:
                kind, text = msgs.get_nowait()
                if kind == "log":
                    append(text)
                elif kind == "done":
                    btn.configure(state="normal")
                    append("Tamamlandı.")
                    messagebox.showinfo(APP_NAME, "Çıktı hazır:\n" + text)
                elif kind == "error":
                    btn.configure(state="normal")
                    append("HATA: " + text)
                    messagebox.showerror(APP_NAME, text)
        except queue.Empty:
            pass
        root.after(150, poll)

    btn.configure(command=start)
    if not aud_var.get():
        append("Audiveris bulunamadı. PDF/JPEG için Audiveris kurulmalı "
               "(MusicXML dosyaları Audiveris olmadan da çevrilebilir).")
    poll()
    root.mainloop()


def main() -> None:
    if len(sys.argv) > 1:
        sys.exit(run_cli(sys.argv[1:]))
    run_gui()
