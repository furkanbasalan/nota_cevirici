"""MusicXML -> PDF.

Yol 1: Verovio (yerleşik) ile SVG üretip Edge/Chrome ile PDF'e yazdırmak.
Yol 2: MuseScore komut satırı.
Yol 3 (son çare): sayfaları HTML olarak kaydedip açmak; kullanıcı Ctrl+P ile PDF kaydeder.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

Log = Callable[[str], None]
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _existing(paths):
    for p in paths:
        if p and Path(p).is_file():
            return str(p)
    return None


def find_browser() -> str | None:
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    return _existing([
        Path(pf86) / "Microsoft/Edge/Application/msedge.exe",
        Path(pf) / "Microsoft/Edge/Application/msedge.exe",
        Path(pf) / "Google/Chrome/Application/chrome.exe",
        Path(pf86) / "Google/Chrome/Application/chrome.exe",
        Path(local) / "Google/Chrome/Application/chrome.exe" if local else None,
        shutil.which("msedge"), shutil.which("chrome"),
    ])


def find_musescore() -> str | None:
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    return _existing([
        Path(pf) / "MuseScore 4/bin/MuseScore4.exe",
        Path(pf) / "MuseScore 3/bin/MuseScore3.exe",
        Path(pf86) / "MuseScore 3/bin/MuseScore3.exe",
        shutil.which("MuseScore4"), shutil.which("MuseScore3"), shutil.which("mscore"),
    ])


def _verovio_pages(xml_bytes: bytes) -> list[str]:
    import verovio  # yerleşik paket

    tk = verovio.toolkit()
    options = {
        "pageWidth": 2100,
        "pageHeight": 2970,
        "scale": 40,
        "svgViewBox": True,
        "adjustPageHeight": False,
        "breaks": "auto",
    }
    try:
        tk.setOptions(options)
    except TypeError:
        tk.setOptions(json.dumps(options))
    if not tk.loadData(xml_bytes.decode("utf-8")):
        raise RuntimeError("Verovio MusicXML dosyasını okuyamadı.")
    return [tk.renderToSVG(i) for i in range(1, tk.getPageCount() + 1)]


def _html(svgs: list[str]) -> str:
    pages = "\n".join(f'<div class="page">{svg}</div>' for svg in svgs)
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Notalar</title><style>'
        "@page{size:A4;margin:0}html,body{margin:0;padding:0}"
        ".page{width:210mm;height:296mm;overflow:hidden;break-after:page;page-break-after:always}"
        ".page:last-child{break-after:auto;page-break-after:auto}"
        ".page svg{width:100%;height:100%;display:block}"
        f"</style></head><body>{pages}</body></html>"
    )


def _profile_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    p = Path(base) / "NotaCevirici" / "browser-profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _browser_pdf(svgs: list[str], pdf_path: Path, browser: str, log: Log) -> bool:
    profile = _profile_dir()
    common = ["--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
              "--no-default-browser-check", "--disable-extensions"]
    attempts = [
        ["--headless=new", f"--user-data-dir={profile}"],
        ["--headless", f"--user-data-dir={profile}"],
        ["--headless=new"],
    ]
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "score.html"
        html_path.write_text(_html(svgs), encoding="utf-8")
        tmp_pdf = Path(tmp) / "score.pdf"  # basit bir yola yaz, sonra kopyala
        for extra in attempts:
            if tmp_pdf.exists():
                tmp_pdf.unlink()
            cmd = [browser, *extra, *common, f"--print-to-pdf={tmp_pdf}", html_path.as_uri()]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                                      timeout=180, creationflags=NO_WINDOW)
                err = (proc.stderr or "").strip()[-300:]
            except Exception as e:  # noqa: BLE001
                err = str(e)
            for _ in range(20):  # dosyanın yazılmasını en fazla ~10 sn bekle
                if tmp_pdf.is_file() and tmp_pdf.stat().st_size > 0:
                    break
                time.sleep(0.5)
            if tmp_pdf.is_file() and tmp_pdf.stat().st_size > 0:
                shutil.copyfile(tmp_pdf, pdf_path)
                return True
            log(f"Tarayıcı denemesi başarısız ({' '.join(extra[:1])}): {err}")
    return False


def _musescore_pdf(xml_bytes: bytes, pdf_path: Path, exe: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "score.musicxml"
        src.write_bytes(xml_bytes)
        subprocess.run([exe, "-o", str(pdf_path), str(src)], capture_output=True,
                       timeout=300, creationflags=NO_WINDOW)
    if not pdf_path.is_file():
        raise RuntimeError("MuseScore PDF üretemedi.")


def musicxml_to_pdf(xml_bytes: bytes, pdf_path: Path, log: Log) -> Path:
    """PDF üretir ve üretilen dosyanın yolunu döndürür (son çare: .html)."""
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    svgs: list[str] = []
    try:
        log("Notalar çiziliyor (Verovio)...")
        svgs = _verovio_pages(xml_bytes)
        log(f"{len(svgs)} sayfa çizildi.")
    except Exception as e:  # noqa: BLE001
        errors.append(f"Verovio: {e}")
        log(f"Uyarı: {e}")

    browser = find_browser()
    if svgs and browser:
        log("PDF yazılıyor (Edge/Chrome)...")
        if _browser_pdf(svgs, pdf_path, browser, log):
            return pdf_path
        errors.append("Tarayıcı PDF üretemedi.")
    elif svgs:
        errors.append("Edge veya Chrome bulunamadı.")

    muse = find_musescore()
    if muse:
        try:
            log("Yedek yol: MuseScore ile PDF üretiliyor...")
            _musescore_pdf(xml_bytes, pdf_path, muse)
            return pdf_path
        except Exception as e:  # noqa: BLE001
            errors.append(f"MuseScore: {e}")

    if svgs:
        html_path = pdf_path.with_suffix(".html")
        html_path.write_text(_html(svgs), encoding="utf-8")
        log("PDF otomatik üretilemedi. Notalar bir web sayfası olarak kaydedildi ve "
            "açılıyor: sayfada Ctrl+P → 'PDF olarak kaydet' deyin.")
        try:
            os.startfile(str(html_path))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        return html_path

    raise RuntimeError("PDF üretilemedi.\n" + "\n".join(errors))
