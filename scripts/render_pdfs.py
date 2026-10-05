#!/usr/bin/env python3
"""Gera cinco PDFs atuais; nomes legados preservados por compatibilidade."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
    'README.md':'README.pdf',
    'SINCRONIZACAO_WUG_NETBOX.md':'SINCRONIZACAO_IMC_NETBOX.pdf',
    'ALTERACOES_REALIZADAS.md':'ALTERACOES_REALIZADAS.pdf',
    'LISTA_DE_ARQUIVOS.md':'LISTA_DE_ARQUIVOS.pdf',
    'REQUISITOS_WUG_NETBOX.md':'Requisitos-Permissoes-Dependencias-Servidor-Linux-IMC-NetBox.pdf',
}

def inline(text):
    text=escape(text.replace('->','→'))
    text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1 (\2)',text)
    text=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    return text.replace('→','-&gt;')

def render(source,destination):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyWUG',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=7,splitLongWords=True))
    styles['Title'].fontSize=21; styles['Title'].leading=26; styles['Title'].textColor=colors.HexColor('#173653')
    styles['Heading2'].fontSize=13; styles['Heading2'].leading=18; styles['Heading2'].textColor=colors.HexColor('#173653')
    code_style=ParagraphStyle('CodeWUG',fontName='Courier',fontSize=7.5,leading=11,backColor=colors.HexColor('#f0f3f6'),borderPadding=7,spaceAfter=10)
    flow=[]; paragraph=[]; code=[]; in_code=False
    def flush():
        if paragraph:
            flow.append(Paragraph(inline(' '.join(paragraph)),styles['BodyWUG'])); paragraph.clear()
    for line in source.read_text().splitlines():
        if line.startswith('```'):
            flush()
            if in_code:
                flow.append(Preformatted('\n'.join(code),code_style,maxLineLength=94));code=[]
            in_code=not in_code;continue
        if in_code: code.append(line);continue
        if not line.strip(): flush();continue
        if line.startswith('# '): flush();flow.append(Paragraph(inline(line[2:]),styles['Title']));continue
        if line.startswith('## '): flush();flow.append(Paragraph(inline(line[3:]),styles['Heading2']));continue
        if line.startswith('- '):
            flush();flow.append(Paragraph('- '+inline(line[2:]),styles['BodyWUG']));continue
        paragraph.append(line)
    flush()
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#c8d3df'));canvas.line(42,41,A4[0]-42,41)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#52677b'))
        canvas.drawString(42,28,'WhatsUp Gold -> NetBox | Código validado offline; homologação pendente')
        canvas.drawRightString(A4[0]-42,28,str(doc.page))
    SimpleDocTemplate(str(destination),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=57,
                      title=source.stem,author='Projeto WhatsUp Gold - NetBox').build(flow,onFirstPage=footer,onLaterPages=footer)
    print(destination.name)
if __name__=='__main__':
    for source,destination in SOURCES.items(): render(ROOT/source,ROOT/destination)
