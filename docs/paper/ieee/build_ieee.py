"""Build the two-column IEEE-style .docx from paper.md (pandoc) and fix up layout."""
import copy
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

here = Path(__file__).parent
raw, out = here / "raw.docx", here / "ATLAS_IEEE_Conference_Paper.docx"
subprocess.run(["pandoc", "paper.md", "-o", str(raw), "--from", "markdown+tex_math_dollars"],
               cwd=here, check=True)

doc = Document(raw)
FONT = "Times New Roman"


def set_font(style, size, bold=None, italic=None):
    style.font.name = FONT
    style.font.size = Pt(size)
    if style.element.rPr is not None and style.element.rPr.rFonts is not None:
        style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        for a in ("w:ascii", "w:hAnsi", "w:cs"):
            style.element.rPr.rFonts.set(qn(a), FONT)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            style.element.rPr.rFonts.attrib.pop(qn(a), None)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    style.font.color.rgb = None


for s in doc.styles:
    if s.type == 1:
        try:
            set_font(s, 10)
        except Exception:
            pass

S = {s.name: s for s in doc.styles}
set_font(S["Title"], 24, bold=False)
names = list(S)
for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
    if name in names:
        st = doc.styles[name]
        st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        st.paragraph_format.space_after = Pt(4)
        st.paragraph_format.space_before = Pt(0)
set_font(S["Heading 1"], 10, bold=False)
set_font(S["Heading 2"], 10, bold=False, italic=True)
for n in ("Heading 1", "Heading 2"):
    S[n].paragraph_format.space_before = Pt(8)
    S[n].paragraph_format.space_after = Pt(4)
    S[n].paragraph_format.keep_with_next = True

# Roman-numeral / lettered heading numbers, IEEE style
roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
h1 = h2 = 0
for p in doc.paragraphs:
    if p.style.name == "Heading 1":
        t = p.text.strip()
        if t.lower() in ("references", "code and data availability"):  # unnumbered back matter
            label = t.upper()
        else:
            h1 += 1
            h2 = 0
            label = f"{roman[h1 - 1]}. {t.upper()}"
        for r in p.runs[1:]:
            r.text = ""
        p.runs[0].text = label
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif p.style.name == "Heading 2":
        h2 += 1
        t = p.text
        for r in p.runs[1:]:
            r.text = ""
        p.runs[0].text = f"{chr(64 + h2)}. {t}"

for p in doc.paragraphs:
    sn = p.style.name
    if sn in ("Title", "Author"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif sn == "Reference":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        for r in p.runs:
            r.font.size = Pt(8)
    elif sn in ("Image Caption", "Table Caption", "Caption"):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.size = Pt(8)
        if sn == "Table Caption":
            p.paragraph_format.keep_with_next = True
    elif sn == "Abstract":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for r in p.runs:
            r.font.size = Pt(9)
            r.bold = True
    if any(r._r.xpath(".//w:drawing") for r in p.runs):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True

# Tables: horizontal rules only, 8 pt
for t in doc.tables:
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "000000")
        borders.append(e)
    t._tbl.tblPr.append(borders)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    r.font.size = Pt(8)

# Page: US Letter; title/abstract single column, body two columns
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.75)
sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(1.0)
sectPr = sec._sectPr

last_abs = [p for p in doc.paragraphs if p.style.name == "Abstract"][-1]
front = copy.deepcopy(sectPr)
for c in front.findall(qn("w:cols")):
    front.remove(c)
typ = OxmlElement("w:type")
typ.set(qn("w:val"), "continuous")
front.insert(0, typ)
cols1 = OxmlElement("w:cols")
cols1.set(qn("w:num"), "1")
# schema order: cols must precede docGrid
grid = front.find(qn("w:docGrid"))
(grid.addprevious(cols1) if grid is not None else front.append(cols1))
last_abs._p.get_or_add_pPr().append(front)

for c in sectPr.findall(qn("w:cols")):
    sectPr.remove(c)
cols = OxmlElement("w:cols")
cols.set(qn("w:num"), "2")
cols.set(qn("w:space"), "360")
grid = sectPr.find(qn("w:docGrid"))
(grid.addprevious(cols) if grid is not None else sectPr.append(cols))

# Front matter (title + 3-column author block) is hand-laid-out in front_matter.docx; splice it in
# ahead of the generated abstract, replacing pandoc's Title/Author paragraphs.
front_src = here / "front_matter.docx"
if front_src.exists():
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    fdoc = Document(front_src)
    first_abs = next(p for p in doc.paragraphs if p.style.name == "Abstract")._p
    for p in [p for p in doc.paragraphs if p.style.name in ("Title", "Author")]:
        p._p.getparent().remove(p._p)
    rid = qn("r:id")
    for el in fdoc.element.body.iterchildren():
        if el.tag == qn("w:p") and el.xpath("string(.)").strip().startswith("Abstract"):
            break
        el = copy.deepcopy(el)
        for h in el.iter(qn("w:hyperlink")):
            if h.get(rid):
                h.set(rid, doc.part.relate_to(fdoc.part.rels[h.get(rid)].target_ref, RT.HYPERLINK, is_external=True))
        first_abs.addprevious(el)

doc.save(out)
print("wrote", out)
