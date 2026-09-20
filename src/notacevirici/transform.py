"""MusicXML üzerinde anahtar dönüşümü.

Kural (kullanıcı tanımı):
  Keman anahtarı (2. çizgide sol)  ->  Alto anahtarı (3. çizgide do)
  Nota isimleri aynı kalır, her nota bir oktav aşağı yazılır.
  Böylece 2. çizgideki sol, 1. ve 2. çizgi arasındaki boşluğa gelir
  (portede her nota tam bir basamak aşağı kayar).

Yalnızca sade keman anahtarı (G, line=2, oktav değişimi yok) dönüştürülür.
Diğer anahtarlar (fa, do, 8'li keman vb.) olduğu gibi bırakılır.
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field


@dataclass
class ConvertResult:
    xml_bytes: bytes
    clefs_converted: int = 0
    notes_shifted: int = 0
    notes_total: int = 0
    clefs_found: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def read_musicxml(data: bytes) -> bytes:
    """.mxl (zip) veya düz MusicXML baytlarını düz XML baytlarına çevirir."""
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root_path = None
            if "META-INF/container.xml" in zf.namelist():
                container = ET.fromstring(zf.read("META-INF/container.xml"))
                for rf in container.iter():
                    if rf.tag.endswith("rootfile") and rf.get("full-path"):
                        root_path = rf.get("full-path")
                        break
            if root_path is None:
                candidates = [
                    n for n in zf.namelist()
                    if n.lower().endswith((".xml", ".musicxml")) and not n.startswith("META-INF")
                ]
                if not candidates:
                    raise ValueError("MXL içinde MusicXML dosyası bulunamadı.")
                root_path = candidates[0]
            return zf.read(root_path)
    return data


def _is_plain_treble(clef: ET.Element) -> bool:
    sign = (clef.findtext("sign") or "").strip()
    if sign != "G":
        return False
    line = (clef.findtext("line") or "2").strip()
    if line != "2":
        return False
    octave_change = (clef.findtext("clef-octave-change") or "0").strip()
    return octave_change in ("0", "")


def _shift_octave(el: ET.Element | None, tag: str, result: ConvertResult) -> bool:
    """el altındaki <tag> (octave / display-octave) değerini 1 azaltır."""
    if el is None:
        return False
    oct_el = el.find(tag)
    if oct_el is None or oct_el.text is None:
        return False
    try:
        value = int(oct_el.text.strip())
    except ValueError:
        return False
    if value <= 0:
        result.warnings.append("Bir nota 0. oktavın altına inemedi; olduğu gibi bırakıldı.")
        return False
    oct_el.text = str(value - 1)
    return True


def convert_musicxml(data: bytes) -> ConvertResult:
    """Keman anahtarını alto anahtarına çevirir, notaları bir oktav aşağı alır."""
    xml_bytes = read_musicxml(data)
    root = ET.fromstring(xml_bytes)
    result = ConvertResult(xml_bytes=b"")

    for part in root.iter("part"):
        # staff numarası -> bu porte şu an dönüştürülmüş (alto) mü?
        converted: dict[str, bool] = {}
        for measure in part.findall("measure"):
            for child in list(measure):
                if child.tag == "attributes":
                    for clef in child.findall("clef"):
                        num = clef.get("number", "1")
                        label = (clef.findtext("sign") or "?").strip() + (clef.findtext("line") or "").strip()
                        oc = (clef.findtext("clef-octave-change") or "").strip()
                        if oc and oc != "0":
                            label += f"({oc})"
                        if label not in result.clefs_found:
                            result.clefs_found.append(label)
                        if _is_plain_treble(clef):
                            sign = clef.find("sign")
                            sign.text = "C"
                            line = clef.find("line")
                            if line is None:
                                line = ET.SubElement(clef, "line")
                            line.text = "3"
                            converted[num] = True
                            result.clefs_converted += 1
                        else:
                            converted[num] = False
                elif child.tag == "note":
                    result.notes_total += 1
                    staff = (child.findtext("staff") or "1").strip()
                    if not converted.get(staff, False):
                        continue
                    shifted = False
                    shifted |= _shift_octave(child.find("pitch"), "octave", result)
                    shifted |= _shift_octave(child.find("unpitched"), "display-octave", result)
                    shifted |= _shift_octave(child.find("rest"), "display-octave", result)
                    if shifted:
                        result.notes_shifted += 1

    if result.clefs_converted == 0:
        if not result.clefs_found:
            result.warnings.append(
                "Tanınan çıktıda hiç anahtar bulunamadı; nota tanıma boş/eksik sonuç vermiş olabilir."
            )
        else:
            result.warnings.append(
                "Dönüştürülecek sade keman anahtarı bulunamadı (bulunanlar: "
                + ", ".join(result.clefs_found) + ")."
            )

    out = io.BytesIO()
    ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)
    result.xml_bytes = out.getvalue()
    return result
