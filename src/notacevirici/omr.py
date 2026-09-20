"""Audiveris ile nota tanıma (görüntü/PDF -> MusicXML)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

Log = Callable[[str], None]

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def candidate_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("AUDIVERIS_EXE")
    if env:
        paths.append(Path(env))
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if base:
            paths.append(Path(base) / "Audiveris" / "Audiveris.exe")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        paths.append(Path(local) / "Programs" / "Audiveris" / "Audiveris.exe")
    for name in ("Audiveris", "audiveris"):
        found = shutil.which(name)
        if found:
            paths.append(Path(found))
    return paths


def find_audiveris(saved: str | None = None) -> str | None:
    if saved and Path(saved).is_file():
        return saved
    for p in candidate_paths():
        if p.is_file():
            return str(p)
    return None


def ascii_temp_base() -> str:
    """Yalnızca ASCII karakter içeren bir geçici klasör döndürür.

    Audiveris (Java) Türkçe karakterli (ü, ş, ğ, ı...) dosya yollarını Windows'ta
    yanlış çözüyor (ör. 'Masaüstü' -> 'MasaÃ¼stÃ¼'). Bu yüzden Audiveris'e
    yalnızca ASCII yollar veriyoruz.
    """
    candidates = [
        tempfile.gettempdir(),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "NotaCevirici"),
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "NotaCevirici"),
        r"C:\NotaCeviriciTemp",
    ]
    for c in candidates:
        if c.isascii():
            try:
                os.makedirs(c, exist_ok=True)
                return c
            except OSError:
                continue
    return tempfile.gettempdir()


def run_audiveris(exe: str, input_path: Path, out_dir: Path, log: Log,
                  timeout: int = 1800) -> list[Path]:
    """Girdiyi tanır ve üretilen MusicXML dosyalarının listesini döndürür."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if not input_path.is_file():
        raise RuntimeError(f"Girdi dosyası bulunamadı: {input_path}")
    # Türkçe karakterli yolları önlemek için girdiyi ASCII adlı bir kopyaya al.
    safe_input = out_dir.parent / ("input" + input_path.suffix.lower())
    shutil.copyfile(input_path, safe_input)
    if not (str(safe_input).isascii() and str(out_dir).isascii()):
        log("Uyarı: geçici klasör yolunda ASCII olmayan karakter var; Audiveris hata verebilir.")
    cmd = [exe, "-batch", "-transcribe", "-export", "-output", str(out_dir), str(safe_input)]
    log("Komut: " + " ".join(cmd))
    log("Nota tanıma başlatıldı (büyük dosyalarda birkaç dakika sürebilir)...")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace",
            timeout=timeout, creationflags=NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Nota tanıma zaman aşımına uğradı.")
    except OSError as e:
        raise RuntimeError(f"Audiveris çalıştırılamadı: {e}")

    files = sorted(
        p for p in out_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".mxl", ".musicxml", ".xml")
    )
    if not files:
        tail = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-1500:]
        raise RuntimeError(
            "Audiveris nota çıktısı üretemedi. Görüntü kalitesini/çözünürlüğünü "
            "kontrol edin (en az 300 dpi önerilir).\n\nAudiveris çıktısı:\n" + tail
        )
    log(f"Nota tanıma tamamlandı ({len(files)} çıktı).")
    return files
