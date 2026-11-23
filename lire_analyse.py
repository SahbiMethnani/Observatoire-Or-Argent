import base64
import html
import re

import streamlit as st
import streamlit.components.v1 as components
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

HEADING_RE = re.compile(r"^(heading|titre)\s*(\d)$")
ALIGN = {0: "left", 1: "center", 2: "right", 3: "justify"}


def iter_blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)
def images_html(run, doc):
    out = ""
    for blip in run._element.findall(".//" + qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if rid and rid in doc.part.related_parts:
            part = doc.part.related_parts[rid]
            b64 = base64.b64encode(part.blob).decode()
            out += (
                f'<img src="data:{part.content_type};base64,{b64}" '
                f'style="max-width:100%;height:auto;">'
            )
    return out


def run_to_html(run, doc, style_font):
    text = html.escape(run.text).replace("\n", "<br>").replace("\t", "&emsp;")
    font = run.font

    bold = font.bold if font.bold is not None else style_font.bold
    italic = font.italic if font.italic is not None else style_font.italic
    underline = font.underline if font.underline is not None else style_font.underline

    css = []
    if font.color is not None and font.color.rgb is not None:
        css.append(f"color:#{font.color.rgb}")
    if font.size:
        css.append(f"font-size:{font.size.pt}pt")
    if font.name:
        css.append(f"font-family:'{font.name}',sans-serif")

    decorations = []
    if underline:
        decorations.append("underline")
    if font.strike:
        decorations.append("line-through")
    if decorations:
        css.append("text-decoration:" + " ".join(decorations))

    if text:
        if bold:
            text = f"<b>{text}</b>"
        if italic:
            text = f"<i>{text}</i>"
        if font.superscript:
            text = f"<sup>{text}</sup>"
        if font.subscript:
            text = f"<sub>{text}</sub>"
        if css:
            text = f'<span style="{";".join(css)}">{text}</span>'

    return text + images_html(run, doc)


def paragraph_inner_html(p, doc):
    style_font = p.style.font if p.style is not None else Run(p._p, p).font
    parts = []
    for child in p._p.iterchildren():
        if child.tag == qn("w:r"):
            parts.append(run_to_html(Run(child, p), doc, style_font))
        elif child.tag == qn("w:hyperlink"):
            inner = "".join(
                run_to_html(Run(r, p), doc, style_font)
                for r in child.findall(qn("w:r"))
            )
            rid = child.get(qn("r:id"))
            url = doc.part.rels[rid].target_ref if rid in doc.part.rels else None
            parts.append(
                f'<a href="{html.escape(url)}" target="_blank">{inner}</a>' if url else inner
            )
    return "".join(parts)


def paragraph_to_html(p, doc):
    inner = paragraph_inner_html(p, doc)
    style_name = (p.style.name or "").lower() if p.style is not None else ""
    align = ALIGN.get(p.alignment)
    align_css = f"text-align:{align};" if align is not None else ""

    m = HEADING_RE.match(style_name)
    if m:
        level = min(int(m.group(1 if False else 2)), 6)
        return f'<h{level} style="{align_css}">{inner}</h{level}>'
    if style_name in ("title", "titre"):
        return f'<h1 class="doc-title" style="{align_css}">{inner}</h1>'
    if style_name in ("subtitle", "sous-titre"):
        return f'<h2 class="doc-subtitle" style="{align_css}">{inner}</h2>'

    
    pPr = p._p.pPr
    num_pr = pPr.numPr if pPr is not None else None
    if num_pr is not None or "list" in style_name or "liste" in style_name:
        level = 0
        if num_pr is not None and num_pr.ilvl is not None:
            level = int(num_pr.ilvl.val)
        numbered = "number" in style_name or "numéro" in style_name
        marker = "&#8211;" if numbered else ("&bull;" if level == 0 else "&#9702;")
        return (
            f'<div style="margin-left:{24 + level * 24}px;{align_css}">'
            f'{marker}&nbsp;{inner}</div>'
        )

    if not inner.strip():
        return '<p style="margin:0">&nbsp;</p>'
    return f'<p style="{align_css}">{inner}</p>'


def table_to_html(table, doc):
    rows_html = []
    for r_idx, row in enumerate(table.rows):
        cells_html = []
        seen = set()
        for cell in row.cells:
            if id(cell._tc) in seen:          
                continue
            seen.add(id(cell._tc))
            content = "".join(paragraph_to_html(p, doc) for p in cell.paragraphs)
            tag = "th" if r_idx == 0 else "td"
            cells_html.append(f"<{tag}>{content}</{tag}>")
        rows_html.append("<tr>" + "".join(cells_html) + "</tr>")
    return "<table>" + "".join(rows_html) + "</table>"


CSS = """
<style>
  body{font-family:'Segoe UI',Arial,sans-serif;color:#222;background:#fff;
       padding:24px 32px;line-height:1.55;}
  h1,h2,h3,h4,h5,h6{color:#1f3864;margin:1.2em 0 .4em;}
  p{margin:.4em 0;}
  table{border-collapse:collapse;width:100%;margin:12px 0;}
  th,td{border:1px solid #999;padding:6px 10px;vertical-align:top;}
  th{background:#f0f0f0;}
  th p,td p{margin:2px 0;}
  a{color:#0563c1;}
</style>
"""


def docx_to_html(file_path):
    doc = Document(file_path)
    body = "".join(
        table_to_html(b, doc) if isinstance(b, Table) else paragraph_to_html(b, doc)
        for b in iter_blocks(doc)
    )
    return CSS + body


def display_docx(file_path):
    if st.button("Afficher le document méthodologique", key="display_methodological_doc"):
        st.session_state["show_methodo_doc"] = True

    if st.session_state.get("show_methodo_doc"):
        components.html(docx_to_html(file_path), height=800, scrolling=True)