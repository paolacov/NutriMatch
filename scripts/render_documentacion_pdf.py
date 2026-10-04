"""Convierte la documentación técnica en PDF (stdlib, fuentes estándar PDF).

No es parte del motor de NutriMatch. Solo maqueta
`docs/NutriMatch_Documentacion_Tecnica_Completa.md`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "NutriMatch_Documentacion_Tecnica_Completa.md"
PDF_PATH = ROOT / "docs" / "NutriMatch_Documentacion_Tecnica_Completa.pdf"

PAGE_W = 595.28
PAGE_H = 841.89
ML = 48.0
MR = 48.0
MT = 54.0
MB = 46.0
CONTENT_W = PAGE_W - ML - MR

INK = (0.063, 0.137, 0.122)
TIDE = (0.059, 0.420, 0.388)
TIDE_DEEP = (0.039, 0.290, 0.251)
BRICK = (0.769, 0.118, 0.227)
CREAM = (0.969, 0.953, 0.922)
PAPER = (1.0, 0.992, 0.973)
SAND = (0.906, 0.875, 0.827)
MUTE = (0.369, 0.408, 0.392)
RULE = (0.820, 0.780, 0.720)
WHITE = (1.0, 1.0, 1.0)
ROW_ALT = (0.965, 0.945, 0.910)

# Anchos AFM de Helvetica / 1000 em. Lo no listado usa 520 (ligeramente ancho).
_HW = {c: 520 for c in range(32, 127)}
_HW.update(
    {
        32: 278, 33: 278, 34: 355, 35: 556, 36: 556, 37: 889, 38: 667, 39: 191,
        40: 333, 41: 333, 42: 389, 43: 584, 44: 278, 45: 333, 46: 278, 47: 278,
        48: 556, 49: 556, 50: 556, 51: 556, 52: 556, 53: 556, 54: 556, 55: 556,
        56: 556, 57: 556, 58: 278, 59: 278, 60: 584, 61: 584, 62: 584, 63: 556,
        64: 1015, 65: 667, 66: 667, 67: 722, 68: 722, 69: 667, 70: 611, 71: 778,
        72: 722, 73: 278, 74: 500, 75: 667, 76: 556, 77: 833, 78: 722, 79: 778,
        80: 667, 81: 778, 82: 722, 83: 667, 84: 611, 85: 722, 86: 667, 87: 944,
        88: 667, 89: 667, 90: 611, 91: 278, 92: 278, 93: 278, 94: 469, 95: 556,
        96: 333, 97: 556, 98: 556, 99: 500, 100: 556, 101: 556, 102: 278, 103: 556,
        104: 556, 105: 222, 106: 222, 107: 500, 108: 222, 109: 833, 110: 556,
        111: 556, 112: 556, 113: 556, 114: 333, 115: 500, 116: 278, 117: 556,
        118: 500, 119: 722, 120: 500, 121: 500, 122: 500, 123: 334, 124: 260,
        125: 334, 126: 584,
    }
)


def _latin(text: str) -> str:
    repl = {
        "\u202f": " ",
        "\u00a0": " ",
        "\u2009": " ",
        "\u2011": "-",
        "\u2013": "-",
        "\u2014": " - ",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00d7": "x",
        "\u2264": "<=",
        "\u2265": ">=",
        "\u2192": "->",
        "\u2500": "-",
        "\u2502": "|",
        "\u251c": "|",
        "\u2514": "`",
        "\u2510": "+",
        "\u250c": "+",
        "\u2518": "+",
        "\u2524": "|",
        "\u252c": "+",
        "\u2534": "+",
        "\u253c": "+",
        "\u2514": "`",
        "\u2502": "|",
    }
    # box-drawing runes used in the repo map
    text = (
        text.replace("├──", "|--")
        .replace("└──", "`--")
        .replace("│", "|")
    )
    out = []
    for ch in text:
        if ch in repl:
            out.append(repl[ch])
        elif ord(ch) < 256:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def text_width(text: str, size: float, mono: bool = False, bold: bool = False) -> float:
    if mono:
        return len(text) * size * 0.6
    scale = 1.06 if bold else 1.0
    return sum(_HW.get(ord(c), 540) for c in text) * size / 1000.0 * scale


def pdf_escape(text: str) -> str:
    raw = _latin(text).encode("latin-1", errors="replace")
    out = bytearray()
    for b in raw:
        if b in (0x5C, 0x28, 0x29):
            out.extend(b"\\" + bytes((b,)))
        else:
            out.append(b)
    return out.decode("latin-1")


@dataclass
class Atom:
    text: str
    kind: str  # normal, bold, code


def parse_inline(text: str) -> list[Atom]:
    text = _latin(text)
    atoms: list[Atom] = []
    i = 0
    buf = []
    kind = "normal"

    def flush() -> None:
        if buf:
            atoms.append(Atom("".join(buf), kind))
            buf.clear()

    while i < len(text):
        if text.startswith("**", i):
            flush()
            j = text.find("**", i + 2)
            if j == -1:
                buf.append(text[i])
                i += 1
                continue
            atoms.append(Atom(text[i + 2 : j], "bold"))
            i = j + 2
            continue
        if text[i] == "`":
            flush()
            j = text.find("`", i + 1)
            if j == -1:
                buf.append(text[i])
                i += 1
                continue
            atoms.append(Atom(text[i + 1 : j], "code"))
            i = j + 1
            continue
        buf.append(text[i])
        i += 1
    flush()
    return [a for a in atoms if a.text]


def atom_width(atom: Atom, size: float) -> float:
    if atom.kind == "code":
        return text_width(atom.text, size * 0.92, mono=True) + 2
    return text_width(atom.text, size, bold=atom.kind == "bold")


def _split_token(text: str, kind: str, width: float, size: float) -> list[str]:
    """Parte un token más ancho que la línea, primero por `_` `/` `.`."""
    if atom_width(Atom(text, kind), size) <= width:
        return [text]
    pieces: list[str] = []
    buf = ""
    for i, ch in enumerate(text):
        trial = buf + ch
        too_wide = atom_width(Atom(trial, kind), size) > width and buf
        boundary = ch in "_/." and buf and atom_width(Atom(buf + ch, kind), size) > width * 0.72
        if too_wide or (boundary and i < len(text) - 1):
            pieces.append(buf)
            buf = ch
        else:
            buf = trial
    if buf:
        pieces.append(buf)
    return pieces or [text]


def wrap_atoms(atoms: list[Atom], width: float, size: float) -> list[list[Atom]]:
    lines: list[list[Atom]] = []
    cur: list[Atom] = []
    used = 0.0

    def newline() -> None:
        nonlocal used
        if cur:
            lines.append(list(cur))
            cur.clear()
        used = 0.0

    def push_piece(text: str, kind: str) -> None:
        nonlocal used
        if text == "":
            return
        if not cur:
            text = text.lstrip(" ")
            if not text:
                return
        piece_w = atom_width(Atom(text, kind), size)
        if cur and used + piece_w > width:
            newline()
            text = text.lstrip(" ")
            if not text:
                return
            piece_w = atom_width(Atom(text, kind), size)
        if piece_w > width:
            chunks = _split_token(text, kind, width, size)
            if chunks == [text]:
                cur.append(Atom(text, kind))
                used += piece_w
                return
            for chunk in chunks:
                push_piece(chunk, kind)
            return
        cur.append(Atom(text, kind))
        used += piece_w

    for atom in atoms:
        for part in re.split(r"(\s+)", atom.text):
            if part:
                push_piece(part, atom.kind)
    if cur:
        lines.append(list(cur))
    return lines or [[]]


@dataclass
class Block:
    kind: str
    text: str = ""
    rows: list[list[str]] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    level: int = 0


def parse_md(src: str) -> list[Block]:
    lines = src.replace("\r\n", "\n").split("\n")
    blocks: list[Block] = []
    i = 0
    para: list[str] = []

    def flush_para() -> None:
        if para:
            blocks.append(Block("p", text=" ".join(x.strip() for x in para)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush_para()
            kind = "diagram" if "diagram" in line else "code"
            i += 1
            body: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i].rstrip("\n"))
                i += 1
            blocks.append(Block(kind, lines=body))
            i += 1
            continue
        if line.strip() == "---":
            flush_para()
            blocks.append(Block("hr"))
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*-+", lines[i + 1]):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if re.match(r"^\|\s*-+", lines[i]):
                    i += 1
                    continue
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            blocks.append(Block("table", rows=rows))
            continue
        if line.startswith("#"):
            flush_para()
            level = len(line) - len(line.lstrip("#"))
            blocks.append(Block("h", text=line[level:].strip(), level=level))
            i += 1
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush_para()
            blocks.append(Block("li", text=m.group(3).strip(), level=1 if m.group(2)[0].isdigit() else 0))
            # keep numbering only as bullet; the text already reads as prose
            i += 1
            continue
        if not line.strip():
            flush_para()
            i += 1
            continue
        para.append(line)
        i += 1
    flush_para()
    return blocks


class Canvas:
    def __init__(self) -> None:
        self.pages: list[list[str]] = []
        self.ops: list[str] = []
        self.y = 0.0
        self.max_x = 0.0
        self.content_height: list[float] = []
        self._page_start_y = 0.0

    def new_page(self) -> None:
        if self.pages or self.ops:
            used = self._page_start_y - self.y
            self.content_height.append(max(0.0, used))
            self.pages.append(self.ops)
        self.ops = []
        self.y = PAGE_H - MT
        self._page_start_y = self.y
        self.rect(0, 0, PAGE_W, PAGE_H, CREAM)
        # encabezado
        self.rect(0, PAGE_H - 28, PAGE_W, 28, TIDE)
        self.text(ML, PAGE_H - 18, "NutriMatch", "F2", 9, WHITE)
        self.text(PAGE_W - MR - 248, PAGE_H - 18, "Documentación técnica y metodológica", "F1", 8, (0.90, 0.95, 0.93))
        self.y = PAGE_H - MT

    def finish(self) -> None:
        used = self._page_start_y - self.y
        self.content_height.append(max(0.0, used))
        self.pages.append(self.ops)

    def need(self, h: float) -> None:
        if self.y - h < MB:
            self.new_page()

    def rect(self, x: float, y: float, w: float, h: float, color: tuple[float, float, float]) -> None:
        r, g, b = color
        self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: tuple[float, float, float], width: float = 0.6) -> None:
        r, g, b = color
        self.ops.append(
            f"{width:.2f} w {r:.3f} {g:.3f} {b:.3f} RG {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
        )

    def text(self, x: float, baseline: float, s: str, font: str, size: float, color: tuple[float, float, float]) -> None:
        r, g, b = color
        esc = pdf_escape(s)
        mono = font in {"F4", "F5"}
        bold = font in {"F2", "F5"}
        self.max_x = max(self.max_x, x + text_width(_latin(s), size, mono=mono, bold=bold))
        self.ops.append(
            f"BT {r:.3f} {g:.3f} {b:.3f} rg /{font} {size:.2f} Tf 1 0 0 1 {x:.2f} {baseline:.2f} Tm ({esc}) Tj ET"
        )

    def draw_atoms(self, x: float, baseline: float, atoms: list[Atom], size: float, color: tuple[float, float, float]) -> None:
        cursor = x
        for atom in atoms:
            if atom.kind == "code":
                sz = size * 0.92
                w = text_width(atom.text, sz, mono=True)
                self.rect(cursor - 0.5, baseline - 2, w + 2, sz + 3, SAND)
                self.text(cursor + 0.4, baseline, atom.text, "F4", sz, TIDE_DEEP)
                cursor += w + 2
            elif atom.kind == "bold":
                self.text(cursor, baseline, atom.text, "F2", size, color)
                cursor += text_width(atom.text, size, bold=True)
            else:
                self.text(cursor, baseline, atom.text, "F1", size, color)
                cursor += text_width(atom.text, size)
        self.max_x = max(self.max_x, cursor)

    def spacer(self, h: float) -> None:
        self.need(h)
        self.y -= h

    def paragraph(self, text: str, size: float = 10.2, color: tuple[float, float, float] = INK, indent: float = 0, gap: float = 3.2) -> None:
        atoms = parse_inline(text)
        lines = wrap_atoms(atoms, CONTENT_W - indent, size)
        for line in lines:
            self.need(size + gap + 1)
            baseline = self.y - size
            self.draw_atoms(ML + indent, baseline, line, size, color)
            self.y = baseline - gap

    def heading(self, text: str, level: int, outline: list[tuple[int, str, int]]) -> None:
        size = {1: 18, 2: 14, 3: 12, 4: 11}.get(level, 11)
        # H1 del markdown es la portada; en el cuerpo los capitulos son ## .
        if level == 1:
            return
        space_before = 16 if level == 2 else 11
        block_h = space_before + size + 8
        if self.y - block_h < MB + 36:
            self.new_page()
        else:
            self.y -= space_before
        page_no = len(self.pages) + 1  # aun no cerrada; + portada y TOC se suman despues
        outline.append((level, _latin(text), page_no))
        self.need(size + 8)
        if level == 2:
            self.rect(ML, self.y - size - 3, 4, size + 2, TIDE)
            self.text(ML + 10, self.y - size, _latin(text), "F2", size, TIDE_DEEP)
        else:
            self.text(ML, self.y - size, _latin(text), "F2", size, INK)
        self.y -= size + 7

    def bullet(self, text: str) -> None:
        atoms = parse_inline(text)
        lines = wrap_atoms(atoms, CONTENT_W - 16, 10)
        for n, line in enumerate(lines):
            self.need(14)
            baseline = self.y - 10
            if n == 0:
                self.text(ML + 2, baseline, "-", "F2", 10, TIDE)
            self.draw_atoms(ML + 14, baseline, line, 10, INK)
            self.y = baseline - 3

    def rule(self) -> None:
        self.need(10)
        y = self.y - 4
        self.line(ML, y, PAGE_W - MR, y, RULE, 0.7)
        self.y = y - 8

    def fence(self, lines: list[str], diagram: bool) -> None:
        body = [_latin(ln) if ln else " " for ln in lines] or [" "]
        longest = max(len(ln) for ln in body)
        size = 8.0
        if longest * size * 0.6 > CONTENT_W - 22:
            size = max(6.2, (CONTENT_W - 22) / max(longest, 1) / 0.6)
        line_h = size + 2.4
        pad = 6
        # partir si no cabe entero, sin dejar el bloque cortado a mitad de glifo
        idx = 0
        while idx < len(body):
            room = self.y - MB - pad * 2
            if room < line_h * 3:
                self.new_page()
                room = self.y - MB - pad * 2
            fit = max(1, int(room // line_h))
            chunk = body[idx : idx + fit]
            idx += len(chunk)
            h = pad * 2 + line_h * len(chunk)
            top = self.y
            self.rect(ML, top - h, CONTENT_W, h, (0.955, 0.945, 0.925) if diagram else (0.97, 0.96, 0.94))
            self.line(ML, top - h, ML, top, TIDE if diagram else MUTE, 2.0)
            baseline = top - pad - size
            for ln in chunk:
                self.text(ML + 8, baseline, ln, "F4", size, INK)
                baseline -= line_h
            self.y = top - h - 8

    def table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        norm = [r + [""] * (ncol - len(r)) for r in rows]
        size = 8.0 if ncol <= 4 else 7.2
        pad_x = 3.5
        # anchos por el contenido, con suelo y techo
        natural = [40.0] * ncol
        for r in norm:
            for i, cell in enumerate(r):
                plain = re.sub(r"[*`]", "", _latin(cell))
                natural[i] = max(natural[i], min(text_width(plain, size, bold=True) + 8, CONTENT_W * 0.55))
        total = sum(natural)
        if total > CONTENT_W:
            scale = CONTENT_W / total
            widths = [w * scale for w in natural]
        else:
            extra = (CONTENT_W - total) / ncol
            widths = [w + extra for w in natural]
        # no dejar una columna por debajo de 36 pt si hay espacio
        header, data = norm[0], norm[1:]

        def row_lines(cells: list[str]) -> list[list[list[Atom]]]:
            wrapped = []
            for i, cell in enumerate(cells):
                atoms = parse_inline(cell)
                wrapped.append(wrap_atoms(atoms, widths[i] - 2 * pad_x, size))
            return wrapped

        def row_height(wrapped: list[list[list[Atom]]]) -> float:
            n = max(len(col) for col in wrapped)
            return n * (size + 2.6) + 5

        def draw_row(cells: list[str], y_top: float, header_row: bool, alt: bool) -> float:
            wrapped = row_lines(cells)
            h = row_height(wrapped)
            bg = TIDE if header_row else (ROW_ALT if alt else PAPER)
            self.rect(ML, y_top - h, CONTENT_W, h, bg)
            x = ML
            color = WHITE if header_row else INK
            for i, col in enumerate(wrapped):
                baseline = y_top - 3.2 - size
                for line in col:
                    if header_row:
                        # encabezado en negrita blanca, sin codigo de color
                        plain = "".join(a.text for a in line)
                        self.text(x + pad_x, baseline, plain, "F2", size, color)
                    else:
                        self.draw_atoms(x + pad_x, baseline, line, size, color)
                    baseline -= size + 2.6
                x += widths[i]
            self.line(ML, y_top - h, ML + CONTENT_W, y_top - h, RULE, 0.3)
            return h

        # header
        wrapped_h = row_lines(header)
        h_h = row_height(wrapped_h)
        first = True
        pending = data
        alt = False
        while True:
            if self.y - h_h - 16 < MB:
                self.new_page()
            draw_row(header, self.y, True, False)
            self.y -= h_h
            while pending:
                wh = row_height(row_lines(pending[0]))
                if self.y - wh < MB:
                    break
                draw_row(pending[0], self.y, False, alt)
                self.y -= wh
                pending = pending[1:]
                alt = not alt
            if not pending:
                break
            self.new_page()
            first = False
        self.y -= 8
        _ = first


def render_body(blocks: list[Block]) -> tuple[Canvas, list[tuple[int, str, int]]]:
    cv = Canvas()
    cv.new_page()
    outline: list[tuple[int, str, int]] = []
    # saltar el H1 (va en la portada) y el subtitulo en negrita suelto
    started = False
    for block in blocks:
        if not started:
            if block.kind == "h" and block.level == 1:
                continue
            if block.kind == "p" and block.text.startswith("**Del procesamiento"):
                continue
            started = True
        if block.kind == "h":
            cv.heading(block.text, block.level, outline)
        elif block.kind == "p":
            cv.paragraph(block.text)
            cv.spacer(4)
        elif block.kind == "li":
            cv.bullet(block.text)
        elif block.kind == "hr":
            cv.rule()
        elif block.kind == "code":
            cv.fence(block.lines, diagram=False)
        elif block.kind == "diagram":
            cv.fence(block.lines, diagram=True)
        elif block.kind == "table":
            cv.table(block.rows)
    cv.finish()
    return cv, outline


def cover_page() -> list[str]:
    ops: list[str] = []

    def add(s: str) -> None:
        ops.append(s)

    def rect(x, y, w, h, color):
        r, g, b = color
        add(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")

    def text(x, y, s, font, size, color):
        r, g, b = color
        add(
            f"BT {r:.3f} {g:.3f} {b:.3f} rg /{font} {size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({pdf_escape(s)}) Tj ET"
        )

    rect(0, 0, PAGE_W, PAGE_H, CREAM)
    rect(0, 0, 18, PAGE_H, TIDE)
    rect(0, 0, PAGE_W, 16, BRICK)
    rect(0, PAGE_H - 16, PAGE_W, 16, TIDE)
    text(ML + 8, PAGE_H - 210, "NUTRIMATCH", "F2", 13, TIDE)
    # titulo en dos lineas
    text(ML + 8, PAGE_H - 260, "NutriMatch", "F2", 28, INK)
    text(ML + 8, PAGE_H - 298, "Documentación técnica", "F2", 22, INK)
    text(ML + 8, PAGE_H - 326, "y metodológica del proyecto", "F2", 22, INK)
    text(ML + 8, PAGE_H - 370, "Del procesamiento de datos al motor de", "F1", 12, MUTE)
    text(ML + 8, PAGE_H - 388, "compatibilidad, API e interfaz Angular", "F1", 12, MUTE)
    rect(ML + 8, PAGE_H - 420, 120, 3, BRICK)
    text(ML + 8, PAGE_H - 460, "Motor Python  ·  FastAPI como transporte  ·  Angular como interfaz", "F1", 10, INK)
    text(ML + 8, PAGE_H - 480, "FastAPI no calcula el ranking. El LLM no calcula el score.", "F2", 10, TIDE_DEEP)
    text(ML + 8, PAGE_H - 540, "Fecha de generación: 29 de septiembre de 2026", "F1", 11, INK)
    text(ML + 8, PAGE_H - 558, "Versión del paquete: 0.1.0", "F1", 11, INK)
    text(ML + 8, PAGE_H - 576, "Fuente: código y archivos del repositorio en esa fecha", "F1", 11, INK)
    text(ML + 8, 80, "Documento de estudio. Describe el sistema que está en el repositorio.", "F3", 10, MUTE)
    text(ML + 8, 66, "Código, datos y motor de esta versión.", "F3", 10, MUTE)
    return ops


def toc_pages(outline: list[tuple[int, str, int]], body_page_offset: int) -> tuple[list[list[str]], int]:
    """Devuelve paginas de indice y cuantas son. body_page_offset es el numero impreso de la primera pagina de cuerpo."""
    cv = Canvas()
    cv.new_page()
    cv.text(ML, cv.y - 18, "Indice", "F2", 18, TIDE_DEEP)
    cv.y -= 36
    for level, title, body_index in outline:
        if level > 3:
            continue
        printed = body_index + body_page_offset - 1
        # body_index es 1-based dentro del cuerpo
        indent = 0 if level == 2 else 14
        size = 11 if level == 2 else 10
        color = INK if level == 2 else MUTE
        label = title
        num = str(printed)
        cv.need(size + 6)
        baseline = cv.y - size
        cv.text(ML + indent, baseline, label, "F2" if level == 2 else "F1", size, color)
        num_w = text_width(num, size, bold=level == 2)
        cv.text(PAGE_W - MR - num_w, baseline, num, "F2" if level == 2 else "F1", size, TIDE)
        # guia
        label_w = text_width(label, size, bold=level == 2)
        x1 = ML + indent + label_w + 6
        x2 = PAGE_W - MR - num_w - 6
        if x2 > x1 + 8:
            cv.line(x1, baseline - 1, x2, baseline - 1, RULE, 0.4)
        cv.y = baseline - 5
    cv.finish()
    return cv.pages, len(cv.pages)


def stamp_number(ops: list[str], number: int, total: int) -> None:
    label = f"{number}  /  {total}"
    w = text_width(label, 9)
    x = (PAGE_W - w) / 2
    r, g, b = MUTE
    esc = pdf_escape(label)
    ops.append(
        f"BT {r:.3f} {g:.3f} {b:.3f} rg /F1 9 Tf 1 0 0 1 {x:.2f} 24 Tm ({esc}) Tj ET"
    )
    ops.append(f"0.82 0.78 0.72 RG 0.6 w {ML:.2f} 36 m {PAGE_W - MR:.2f} 36 l S")


def build_pdf(cover: list[str], toc: list[list[str]], body: list[list[str]]) -> bytes:
    pages = [cover, *toc, *body]
    # objetos: 1 catalog, 2 pages, 3-7 fonts, luego por pagina: page obj + content
    fonts = [
        ("F1", "Helvetica"),
        ("F2", "Helvetica-Bold"),
        ("F3", "Helvetica-Oblique"),
        ("F4", "Courier"),
        ("F5", "Courier-Bold"),
    ]
    n_pages = len(pages)
    # ids
    # 1 catalog, 2 pages parent, 3..7 fonts
    first_font = 3
    first_page_obj = 8
    # each page uses 2 objects
    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    font_refs = " ".join(f"/{name} {first_font + i} 0 R" for i, (name, _) in enumerate(fonts))
    kids = []
    for i in range(n_pages):
        page_id = first_page_obj + i * 2
        content_id = page_id + 1
        kids.append(f"{page_id} 0 R")
        stream = "\n".join(pages[i]).encode("latin-1", errors="replace")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
            f"/Contents {content_id} 0 R /Resources << /Font << {font_refs} >> >> >>"
        ).encode("latin-1")
    objects[2] = f"<< /Type /Pages /Count {n_pages} /Kids [{' '.join(kids)}] >>".encode("latin-1")
    for i, (_name, base) in enumerate(fonts):
        objects[first_font + i] = (
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode("latin-1")
        )

    max_id = max(objects)
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (max_id + 1)
    for i in range(1, max_id + 1):
        offsets[i] = len(out)
        out.extend(f"{i} 0 obj\n".encode("latin-1"))
        out.extend(objects[i])
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {max_id + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for i in range(1, max_id + 1):
        out.extend(f"{offsets[i]:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer << /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1")
    )
    return bytes(out)


def main() -> None:
    src = MD_PATH.read_text(encoding="utf-8")
    blocks = parse_md(src)
    body_cv, outline = render_body(blocks)
    # El indice se numera despues de la portada. Primero se estima con 2 paginas y se reintenta si cambia.
    toc_count = 2
    for _ in range(3):
        # pagina impresa del cuerpo = 1 (portada) + toc_count + indice de cuerpo
        # Queremos que el indice cite el numero de pagina real (portada = 1).
        offset = 1 + toc_count  # pagina impresa de la primera de cuerpo = offset + (body_index-1) wait
        # printed = body_index + body_page_offset - 1
        # queremos printed = toc_count + 1 + body_index  si portada es pagina 1? 
        # paginas: 1 portada, 2.. toc, luego cuerpo.
        # primera de cuerpo = 1 + toc_count + 1 = toc_count + 2
        # printed = body_index + (toc_count + 1)
        # formula usada: printed = body_index + body_page_offset - 1
        # so body_page_offset - 1 = toc_count + 1 => body_page_offset = toc_count + 2
        toc, new_count = toc_pages(outline, body_page_offset=toc_count + 2)
        if new_count == toc_count:
            break
        toc_count = new_count
    cover = cover_page()
    all_pages = [cover, *toc, *body_cv.pages]
    total = len(all_pages)
    for i, ops in enumerate(all_pages, start=1):
        stamp_number(ops, i, total)
    pdf = build_pdf(all_pages[0], all_pages[1 : 1 + len(toc)], all_pages[1 + len(toc) :])
    PDF_PATH.write_bytes(pdf)
    # verificacion estructural
    n_pages = 1 + len(toc) + len(body_cv.pages)
    short = []
    for i, h in enumerate(body_cv.content_height):
        # altura util aproximada 740; menos de 120 pt es una pagina casi vacia
        if h < 120 and i != len(body_cv.content_height) - 1:
            short.append((i + 1, round(h, 1)))
    overflow = body_cv.max_x > PAGE_W - MR + 1
    print(f"pdf={PDF_PATH}")
    print(f"bytes={len(pdf)} pages={n_pages} body={len(body_cv.pages)} toc={len(toc)}")
    print(f"max_x={body_cv.max_x:.1f} limit={PAGE_W - MR:.1f} overflow={overflow}")
    print(f"short_body_pages={short}")
    if overflow or short:
        sys.exit(2)


if __name__ == "__main__":
    main()
