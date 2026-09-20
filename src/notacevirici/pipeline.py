"""Tüm işlem hattı: girdi -> (OMR) -> anahtar dönüşümü -> PDF."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from .omr import ascii_temp_base, run_audiveris
from .render import musicxml_to_pdf
from .transform import convert_musicxml

Log = Callable[[str], None]

IMAGE_PDF = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
MUSICXML = {".mxl", ".musicxml", ".xml"}


def convert_file(input_path: Path, output_pdf: Path, audiveris_exe: str | None,
                 log: Log) -> list[Path]:
    input_path = Path(input_path)
    output_pdf = Path(output_pdf)
    ext = input_path.suffix.lower()
    results: list[Path] = []

    with tempfile.TemporaryDirectory(dir=ascii_temp_base()) as tmp:
        if ext in IMAGE_PDF:
            if not audiveris_exe:
                raise RuntimeError("Audiveris bulunamadı. Lütfen kurun veya konumunu seçin.")
            xml_files = run_audiveris(audiveris_exe, input_path, Path(tmp) / "omr", log)
        elif ext in MUSICXML:
            xml_files = [input_path]
        else:
            raise RuntimeError(f"Desteklenmeyen dosya türü: {ext}")

        for idx, xml_file in enumerate(xml_files, start=1):
            log("Anahtar dönüştürülüyor (keman -> alto, bir oktav aşağı)...")
            res = convert_musicxml(xml_file.read_bytes())
            for w in res.warnings:
                log(f"Uyarı: {w}")
            log(f"Tanınan: {res.notes_total} nota/es, anahtarlar: "
                f"{', '.join(res.clefs_found) or 'yok'}.")
            log(f"{res.clefs_converted} anahtar, {res.notes_shifted} nota/es dönüştürüldü.")

            suffix = "" if len(xml_files) == 1 else f"_{idx}"
            pdf_path = output_pdf.with_name(output_pdf.stem + suffix + output_pdf.suffix)
            xml_out = pdf_path.with_suffix(".musicxml")
            xml_out.write_bytes(res.xml_bytes)  # düzeltme için MuseScore'da açılabilir

            out_path = musicxml_to_pdf(res.xml_bytes, pdf_path, log)
            log(f"Hazır: {out_path}")
            results.append(out_path)
    return results
