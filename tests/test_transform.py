import io
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from notacevirici.transform import convert_musicxml  # noqa: E402

SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Piyano</part-name></score-part>
    <score-part id="P2"><part-name>Keman</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <staves>2</staves>
        <clef number="1"><sign>G</sign><line>2</line></clef>
        <clef number="2"><sign>F</sign><line>4</line></clef>
      </attributes>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><staff>1</staff></note>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>4</duration><staff>2</staff></note>
    </measure>
    <measure number="2">
      <note><rest><display-step>B</display-step><display-octave>4</display-octave></rest><duration>4</duration><staff>1</staff></note>
      <note><pitch><step>F</step><alter>1</alter><octave>5</octave></pitch><duration>4</duration><staff>1</staff></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration></note>
      <attributes><clef><sign>F</sign><line>4</line></clef></attributes>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>4</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def pitches(xml_bytes, part_id):
    root = ET.fromstring(xml_bytes)
    part = [p for p in root.iter("part") if p.get("id") == part_id][0]
    out = []
    for note in part.iter("note"):
        p = note.find("pitch")
        if p is not None:
            out.append(p.findtext("step") + p.findtext("octave"))
    return out


class TransformTest(unittest.TestCase):
    def test_treble_to_alto_one_octave_down(self):
        res = convert_musicxml(SAMPLE)
        # Piyano sağ el: G4->G3, F#5->F#4 ; sol el (fa anahtarı) değişmez
        self.assertEqual(pitches(res.xml_bytes, "P1"), ["G3", "C3", "F4"])
        root = ET.fromstring(res.xml_bytes)
        clefs = [(c.findtext("sign"), c.findtext("line")) for c in root.iter("clef")]
        self.assertEqual(clefs[0], ("C", "3"))
        self.assertEqual(clefs[1], ("F", "4"))

    def test_rest_display_shifted(self):
        res = convert_musicxml(SAMPLE)
        root = ET.fromstring(res.xml_bytes)
        rest = next(root.iter("rest"))
        self.assertEqual(rest.findtext("display-octave"), "3")

    def test_clef_change_midway_stops_shifting(self):
        res = convert_musicxml(SAMPLE)
        # Keman: E4 -> E3 (alto), sonra fa anahtarına geçince C3 değişmez
        self.assertEqual(pitches(res.xml_bytes, "P2"), ["E3", "C3"])

    def test_counts(self):
        res = convert_musicxml(SAMPLE)
        self.assertEqual(res.clefs_converted, 2)
        self.assertEqual(res.notes_shifted, 4)  # G4, rest, F#5, E4
        self.assertFalse(res.warnings)

    def test_mxl_input(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "META-INF/container.xml",
                '<container><rootfiles><rootfile full-path="score.xml"/></rootfiles></container>',
            )
            zf.writestr("score.xml", SAMPLE)
        res = convert_musicxml(buf.getvalue())
        self.assertEqual(pitches(res.xml_bytes, "P1")[0], "G3")

    def test_diagnostics(self):
        res = convert_musicxml(SAMPLE)
        self.assertEqual(res.notes_total, 6)
        self.assertEqual(res.clefs_found, ["G2", "F4"])

    def test_no_treble_warns(self):
        xml = SAMPLE.replace(b"<sign>G</sign>", b"<sign>F</sign>")
        res = convert_musicxml(xml)
        self.assertEqual(res.clefs_converted, 0)
        self.assertTrue(res.warnings)


if __name__ == "__main__":
    unittest.main()
