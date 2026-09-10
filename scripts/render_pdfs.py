#!/usr/bin/env python3
"""PDFs textuais reproduzíveis derivados dos Markdown, sem dependências extras."""
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['README', 'SINCRONIZACAO_IMC_NETBOX', 'ALTERACOES_REALIZADAS',
           'LISTA_DE_ARQUIVOS', 'Requisitos-Permissoes-Dependencias-Servidor-Linux-IMC-NetBox']

def render(source, destination):
    lines = []
    text = source.read_text(encoding='utf-8')
    text = text.replace('→', '->').replace('—', '-').replace('–', '-')
    for line in text.splitlines():
        if line.startswith('```'):
            continue
        line = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'\1 (\2)', line)
        line = line.replace('`', '').replace('**', '')
        lines.extend(textwrap.wrap(line, width=86, replace_whitespace=False) or [''])
    pages = [lines[i:i+49] for i in range(0, len(lines), 49)] or [[]]
    objects = [b'', b'', b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>']
    page_ids = []
    for number, page in enumerate(pages, 1):
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        commands = ['BT /F1 10 Tf 48 750 Td 14 TL']
        for line in page:
            line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append('(' + line + ') Tj T*')
        commands.append('ET BT /F1 9 Tf 48 32 Td (Piloto iMC - NetBox | ' + str(number) + '/' + str(len(pages)) + ') Tj ET')
        stream = '\n'.join(commands).encode('cp1252', 'replace')
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[1] = ('<< /Type /Pages /Kids [' + ' '.join(f'{p} 0 R' for p in page_ids) +
                  f'] /Count {len(page_ids)} >>').encode()
    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(data)
    data.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    destination.write_bytes(data)
    print(destination.name, len(pages), 'páginas')

if __name__ == '__main__':
    for name in SOURCES:
        render(ROOT / (name + '.md'), ROOT / (name + '.pdf'))
