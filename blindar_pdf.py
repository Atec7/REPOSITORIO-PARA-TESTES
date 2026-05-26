import sys
import os
import random

def corrupt_xref_table(data: bytes) -> bytes:
    """Corrompe a xref table e trailer sem quebrar a renderizacao."""
    lines = data.split(b'\n')
    result = []
    xref_start = None
    xref_end = None

    for i, line in enumerate(lines):
        if line.strip().startswith(b'xref'):
            xref_start = i
        elif xref_start is not None and xref_end is None:
            stripped = line.strip()
            if stripped.startswith(b'trailer') or stripped.startswith(b'startxref'):
                xref_end = i

    if xref_start is not None and xref_end is not None:
        for i in range(xref_start, xref_end):
            if i >= len(lines):
                break
            stripped = lines[i].strip()
            if stripped and stripped[0:1].isdigit() and b' ' in stripped:
                parts = stripped.split(b' ')
                if 2 <= len(parts) <= 3:
                    original = lines[i]
                    gen_num = parts[1]
                    lines[i] = original.replace(gen_num, b'99999', 1)
                    result.append(True)
        result_lines = lines
    else:
        result_lines = lines
        result = [False]

    return b'\n'.join(result_lines)


def inject_fake_filter(data: bytes) -> bytes:
    """Adiciona /Filter /FakeFilter nos streams mantendo decodeabilidade."""
    import re
    pattern = rb'(stream\n)(.*?)(\nendstream)'

    def replacer(m):
        prefix = m.group(1)
        content = m.group(2)
        suffix = m.group(3)
        if len(content) > 50:
            return prefix + content + suffix
        return m.group(0)

    replaced = re.sub(pattern, replacer, data, flags=re.DOTALL)
    if replaced == data:
        lines = data.split(b'\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            stripped = line.strip()
            if stripped.startswith(b'/Filter') or stripped.startswith(b'/Subtype'):
                if i + 1 < len(lines) and lines[i + 1].strip() == b'stream':
                    pass
            if stripped == b'stream' and i > 0:
                prev = lines[i - 1].strip()
                if b'/Filter' not in prev and b'/Length' not in prev:
                    lines[i - 1] = lines[i - 1].rstrip() + b'\n/Filter /FakeFilter'
        new_lines = lines
        return b'\n'.join(new_lines)
    return replaced


def corrupt_page_dict(data: bytes) -> bytes:
    """Corrompe sutilmente o dicionario /Pages."""
    lines = data.split(b'\n')
    for i, line in enumerate(lines):
        if b'/Type /Pages' in line or b'/Type /Page' in line:
            lines[i] = line.replace(b'/Type /Pages', b'/Type /PageZ')
    return b'\n'.join(lines)


def inject_garbage_metadata(data: bytes) -> bytes:
    """Injeta metadados malformados."""
    markers = [
        b'</Info>' if b'</Info>' in data else None,
        b'>>' if b'/Metadata' in data else None,
    ]
    for marker in filter(None, markers):
        data = data.replace(marker, marker + b'\n  /X-Converter /Nonexistent\n  /X-Version (999.999)\n  /X-Checksum <00000000000000000000000000000000>\n', 1)
        break
    return data


def break_startxref(data: bytes) -> bytes:
    """Corrompe startxref para apontar para posicao errada."""
    lines = data.split(b'\n')
    for i, line in enumerate(lines):
        if line.strip().startswith(b'startxref'):
            try:
                lines[i+1]
            except IndexError:
                continue
            try:
                offset = int(lines[i+1].strip())
                fake_offset = offset + random.randint(1, 50)
                lines[i+1] = str(fake_offset).encode()
            except ValueError:
                continue
            break
    return b'\n'.join(lines)


def corrupt_trailer_dict(data: bytes) -> bytes:
    """Adiciona campos invalidos no trailer."""
    lines = data.split(b'\n')
    for i, line in enumerate(lines):
        if line.strip() == b'trailer' and i + 1 < len(lines):
            lines[i] = line + b'\n  /XRefStm (corrupted)\n  /Prev 0'
            break
    return b'\n'.join(lines)


def blindar_pdf(input_path: str, output_path: str):
    with open(input_path, 'rb') as f:
        data = f.read()

    print(f"[1/6] Corrompendo xref table...")
    data = corrupt_xref_table(data)

    print(f"[2/6] Adicionando filtros invalidos...")
    data = inject_fake_filter(data)

    print(f"[3/6] Corrompendo dicionario de paginas...")
    data = corrupt_page_dict(data)

    print(f"[4/6] Injetando metadados malformados...")
    data = inject_garbage_metadata(data)

    print(f"[5/6] Quebrando startxref...")
    data = break_startxref(data)

    print(f"[6/6] Adulterando trailer...")
    data = corrupt_trailer_dict(data)

    with open(output_path, 'wb') as f:
        f.write(data)

    print(f"\nPDF blindado salvo em: {output_path}")
    print(f"Tamanho original: {os.path.getsize(input_path)} bytes")
    print(f"Tamanho final:    {os.path.getsize(output_path)} bytes")
    print("\n>>> O PDF deve abrir normalmente em visualizadores (Adobe, Chrome, Edge)")
    print(">>> Mas conversores automaticos das plataformas DEVEM quebrar ao processar")


def gerar_pdf_teste(path: str):
    """Gera um PDF simples para demonstracao."""
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Length 44 >>\n"
        b"stream\n"
        b"BT /F1 24 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj\n"
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000358 00000 n \n"
        b"trailer\n"
        b"<< /Size 6 /Root 1 0 R /Info 6 0 R >>\n"
        b"startxref\n"
        b"406\n"
        b"%%EOF\n"
    )
    with open(path, 'wb') as f:
        f.write(content)
    print(f"PDF de teste gerado: {path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        test_pdf = "test_input.pdf"
        gerar_pdf_teste(test_pdf)
        blindar_pdf(test_pdf, "test_output_blindado.pdf")
    else:
        inp = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else inp.replace('.pdf', '_blindado.pdf')
        if not os.path.exists(inp):
            print(f"Erro: arquivo nao encontrado: {inp}")
            sys.exit(1)
        blindar_pdf(inp, out)
