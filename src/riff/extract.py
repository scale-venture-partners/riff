"""Turn a file (or raw text) into a Document of prose Blocks with source locations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from riff.textutil import strip_inline_markdown, word_count

PROSE_KINDS = frozenset({"paragraph", "list_item", "table_cell", "notes"})
SUPPORTED = {".md", ".markdown", ".txt", ".text", ".html", ".htm", ".docx", ".pptx"}


@dataclass
class Block:
    text: str
    kind: str
    line: int
    col: int = 1
    label: str = ""
    level: int = 0
    bold_lead: bool = False
    # (line number, raw line) pairs so regex rules can report exact positions.
    raw_lines: list[tuple[int, str]] = field(default_factory=list)

    @property
    def is_prose(self) -> bool:
        return self.kind in PROSE_KINDS

    @property
    def word_count(self) -> int:
        return word_count(self.text)

    def location(self) -> str:
        return f"{self.label}:" if self.label else f"{self.line}:{self.col}"


@dataclass
class Section:
    """A heading and everything under it -- or, in a deck, one slide.

    Sections nest by heading level: an h3 is a child of the h2 above it. `blocks` holds the section's
    own content; `children` its subsections. A deck's slides are flat, each at level 1, and a slide's
    speaker notes are part of its section.
    """

    title: Block | None
    blocks: list[Block]
    level: int
    label: str
    children: list[Section] = field(default_factory=list)
    # Pictures and charts in the section. riff reads only text, so a section whose evidence is a chart
    # looks unsupported to a text-only judge unless it is told the chart is there.
    visuals: int = 0

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    @property
    def body(self) -> list[Block]:
        """The section's content, its subsections' included, without any headings."""
        out = list(self.blocks)
        for child in self.children:
            out += child.body
        return out

    @property
    def body_text(self) -> str:
        return "\n\n".join(b.text for b in self.body if b.text)

    @property
    def anchor(self) -> Block | None:
        """Where a finding about the whole section is reported."""
        return self.title or (self.blocks[0] if self.blocks else None)


@dataclass
class Document:
    """A file read as a hierarchy: document > sections > titles and paragraphs > sentences.

    `blocks` is the flat sequence of leaf units (paragraphs, list items, table cells, notes, titles
    and headings) in reading order, which is what most rules walk. `sections` groups those blocks
    under their headings -- or slides -- so a rule can judge a whole section, or the document's
    outline, rather than one paragraph at a time.
    """

    path: str
    format: str
    blocks: list[Block]
    _sections: list[Section] | None = field(default=None, repr=False, compare=False)
    # Pictures and charts per slide, for decks (slide number -> count).
    visuals: dict[int, int] = field(default_factory=dict, compare=False)

    @property
    def prose(self) -> list[Block]:
        return [b for b in self.blocks if b.is_prose]

    @property
    def sections(self) -> list[Section]:
        """The top-level sections, each holding its subsections."""
        if self._sections is None:
            self._sections = build_sections(self)
        return self._sections

    def walk_sections(self):
        for section in self.sections:
            yield from section.walk()

    @property
    def outline(self) -> list[tuple[int, str, str]]:
        """(level, label, title) for every titled section, in order: the document read as its headings."""
        return [(s.level, s.label, s.title.text) for s in self.walk_sections() if s.title is not None]

    @property
    def headings(self) -> list[Block]:
        return [b for b in self.blocks if b.kind in ("heading", "title")]

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks if b.text)

    @property
    def word_count(self) -> int:
        return sum(b.word_count for b in self.blocks)


def _slide_number(block: Block) -> int:
    return block.line


def _merge_titles(parts: list[Block]) -> Block:
    """A title set as several paragraphs -- a wrapped line, an accent line -- is one title."""
    first = parts[0]
    if len(parts) == 1:
        return first
    text = " ".join(p.text for p in parts)
    return Block(text=text, kind=first.kind, line=first.line, col=first.col, label=first.label,
                 level=first.level, raw_lines=[(first.line, text)])


def _slide_sections(doc: Document) -> list[Section]:
    sections: dict[int, list[Block]] = {}
    for block in doc.blocks:
        sections.setdefault(_slide_number(block), []).append(block)
    out = []
    for number, blocks in sections.items():
        titles = [b for b in blocks if b.kind == "title"]
        body = [b for b in blocks if b.kind != "title"]
        out.append(Section(title=_merge_titles(titles) if titles else None, blocks=body, level=1,
                           label=f"slide {number}", visuals=doc.visuals.get(number, 0)))
    return out


def _heading_sections(doc: Document) -> list[Section]:
    """Nest sections by heading level. Content before the first heading is an untitled lead section;
    a document title (an HTML <title>, a Word 'Title' paragraph) names the document, not a section."""
    roots: list[Section] = []
    stack: list[Section] = []
    lead: Section | None = None
    for block in doc.blocks:
        if block.kind == "heading":
            level = max(block.level, 1)
            section = Section(title=block, blocks=[], level=level, label=block.location().rstrip(":"))
            while stack and stack[-1].level >= level:
                stack.pop()
            (stack[-1].children if stack else roots).append(section)
            stack.append(section)
        elif block.kind == "title":
            continue
        elif stack:
            stack[-1].blocks.append(block)
        else:
            if lead is None:
                lead = Section(title=None, blocks=[], level=0, label=block.location().rstrip(":"))
                roots.insert(0, lead)
            lead.blocks.append(block)
    return roots


def build_sections(doc: Document) -> list[Section]:
    return _slide_sections(doc) if doc.format == "pptx" else _heading_sections(doc)


def extract(path: str | Path) -> Document:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in SUPPORTED:
        raise ValueError(f"{p}: unsupported file type {suffix!r} (supported: {', '.join(sorted(SUPPORTED))})")
    if suffix == ".docx":
        return extract_docx(p)
    if suffix == ".pptx":
        return extract_pptx(p)
    text = p.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        return extract_html(text, str(p))
    if suffix in (".md", ".markdown"):
        return extract_markdown(text, str(p))
    return extract_text(text, str(p))


# ---------------------------------------------------------------- plain text and markdown

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_SETEXT = re.compile(r"^\s*(=+|-+)\s*$")
_BOLD_LEAD = re.compile(r"^\s*(?:\*\*|__)[^*_]+(?:\*\*|__)")


def extract_text(text: str, name: str = "<text>") -> Document:
    blocks: list[Block] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].strip():
            i += 1
        raw = [(n + 1, lines[n]) for n in range(start, i)]
        body = " ".join(ln.strip() for _, ln in raw)
        blocks.append(Block(text=body, kind="paragraph", line=start + 1, raw_lines=raw))
    return Document(path=name, format="txt", blocks=blocks)


def extract_markdown(text: str, name: str = "<markdown>") -> Document:
    lines = text.splitlines()
    blocks: list[Block] = []
    i = 0
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() not in ("---", "..."):
            j += 1
        i = j + 1
    in_fence = None
    while i < len(lines):
        line = lines[i]
        fence = _FENCE.match(line)
        if fence:
            if in_fence is None:
                in_fence = fence.group(1)
            elif fence.group(1) == in_fence:
                in_fence = None
            i += 1
            continue
        if in_fence or not line.strip() or _TABLE_ROW.match(line) or line.lstrip().startswith("<"):
            i += 1
            continue
        h = _HEADING.match(line)
        if h:
            blocks.append(
                Block(
                    text=strip_inline_markdown(h.group(2)),
                    kind="heading",
                    line=i + 1,
                    level=len(h.group(1)),
                    raw_lines=[(i + 1, line)],
                )
            )
            i += 1
            continue
        li = _LIST_ITEM.match(line)
        if li:
            start = i
            raw = [(i + 1, line)]
            i += 1
            while i < len(lines) and lines[i].strip() and not _LIST_ITEM.match(lines[i]) and lines[i][:1].isspace():
                raw.append((i + 1, lines[i]))
                i += 1
            body = " ".join([li.group(2).strip()] + [ln.strip() for _, ln in raw[1:]])
            blocks.append(
                Block(
                    text=strip_inline_markdown(body),
                    kind="list_item",
                    line=start + 1,
                    col=len(li.group(1)) + 1,
                    bold_lead=bool(_BOLD_LEAD.match(li.group(2))),
                    raw_lines=raw,
                )
            )
            continue
        start = i
        raw = []
        while i < len(lines) and lines[i].strip() and not _HEADING.match(lines[i]) and not _LIST_ITEM.match(lines[i]):
            if _FENCE.match(lines[i]) or _TABLE_ROW.match(lines[i]):
                break
            raw.append((i + 1, lines[i]))
            i += 1
        if len(raw) >= 2 and _SETEXT.match(raw[-1][1]):
            body = " ".join(ln.strip().lstrip("> ").strip() for _, ln in raw[:-1])
            blocks.append(
                Block(
                    text=strip_inline_markdown(body),
                    kind="heading",
                    line=start + 1,
                    level=1 if raw[-1][1].strip().startswith("=") else 2,
                    raw_lines=raw,
                )
            )
            continue
        if raw:
            body = " ".join(ln.strip().lstrip("> ").strip() for _, ln in raw)
            blocks.append(Block(text=strip_inline_markdown(body), kind="paragraph", line=start + 1, raw_lines=raw))
    return Document(path=name, format="md", blocks=blocks)


# ---------------------------------------------------------------- html

_HTML_BLOCKS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "td", "th", "dd", "dt",
                "figcaption", "title")


_CHROME_TAGS = ("nav", "footer", "aside", "form", "button", "select", "dialog")
_CHROME_ROLES = ("navigation", "banner", "contentinfo", "complementary", "search")
_MIN_PARAGRAPH_CHARS = 25


def _text_len(el) -> int:
    return len(el.get_text(" ", strip=True))


def _content_root(soup):
    """The element holding a page's article body, with site chrome removed.

    Prefers the largest <article>, then <main>, then <body>. Within that, narrows to the container whose direct
    paragraphs hold at least half the text, which drops related-post lists and call-to-action sections that sit
    beside the article inside <main>.
    """
    for tag in soup(_CHROME_TAGS):
        tag.decompose()
    for el in soup.find_all(attrs={"role": True}):
        if el.get("role") in _CHROME_ROLES:
            el.decompose()
    articles = soup.find_all("article")
    scope = max(articles, key=_text_len) if articles else (soup.find("main") or soup.body or soup)
    if scope.name == "body" or scope is soup:
        for tag in scope(["header"]):
            tag.decompose()
    weight: dict[int, int] = {}
    parents = {}
    for p in scope.find_all("p"):
        n = _text_len(p)
        if n >= _MIN_PARAGRAPH_CHARS and p.parent is not None:
            weight[id(p.parent)] = weight.get(id(p.parent), 0) + n
            parents[id(p.parent)] = p.parent
    if weight:
        top = max(weight, key=weight.get)
        if weight[top] >= 0.5 * _text_len(scope):
            return parents[top]
    return scope


def extract_html(html: str, name: str = "<html>", *, main_content: bool = False) -> Document:
    """Extract blocks from HTML. With main_content, keep only the article body plus its page title heading."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "pre", "code"]):
        tag.decompose()
    elements = soup.find_all(_HTML_BLOCKS)
    if main_content:
        title = soup.find("h1")
        root = _content_root(soup)
        elements = root.find_all(_HTML_BLOCKS)
        if title is not None and not title.decomposed and title not in elements:
            elements.insert(0, title)
        elements = [el for el in elements if el.name != "title"]
    blocks: list[Block] = []
    for el in elements:
        if el.find(_HTML_BLOCKS):
            continue
        text = el.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        line = getattr(el, "sourceline", None) or 0
        if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            kind, level = "heading", int(el.name[1])
        elif el.name == "title":
            kind, level = "title", 0
        elif el.name == "li":
            kind, level = "list_item", 0
        elif el.name in ("td", "th"):
            kind, level = "table_cell", 0
        else:
            kind, level = "paragraph", 0
        first = next((c for c in el.children if getattr(c, "name", None) or str(c).strip()), None)
        bold_lead = getattr(first, "name", None) in ("strong", "b")
        # Fetched pages are often minified onto one line, so source lines locate nothing; number the blocks.
        label = f"block {len(blocks) + 1}" if main_content else ""
        blocks.append(
            Block(text=text, kind=kind, line=line, level=level, bold_lead=bold_lead, label=label,
                  raw_lines=[(line, text)])
        )
    return Document(path=name, format="html", blocks=blocks)


# ---------------------------------------------------------------- docx and pptx


def extract_docx(path: Path) -> Document:
    import docx

    d = docx.Document(str(path))
    blocks: list[Block] = []
    for idx, para in enumerate(d.paragraphs, 1):
        text = re.sub(r"\s+", " ", para.text).strip()
        if not text:
            continue
        style = (para.style.name if para.style is not None else "") or ""
        kind, level = "paragraph", 0
        if style.startswith("Heading"):
            kind = "heading"
            digits = re.findall(r"\d+", style)
            level = int(digits[0]) if digits else 1
        elif style == "Title":
            kind = "title"
        elif "List" in style:
            kind = "list_item"
        runs = [r for r in para.runs if r.text.strip()]
        bold_lead = bool(runs) and bool(runs[0].bold) and not all(bool(r.bold) for r in runs)
        blocks.append(
            Block(
                text=text,
                kind=kind,
                line=idx,
                label=f"paragraph {idx}",
                level=level,
                bold_lead=bold_lead,
                raw_lines=[(idx, text)],
            )
        )
    for t_idx, table in enumerate(d.tables, 1):
        for r_idx, row in enumerate(table.rows, 1):
            for c_idx, cell in enumerate(row.cells, 1):
                text = re.sub(r"\s+", " ", cell.text).strip()
                if text:
                    label = f"table {t_idx} r{r_idx}c{c_idx}"
                    blocks.append(Block(text=text, kind="table_cell", line=0, label=label, raw_lines=[(0, text)]))
    return Document(path=str(path), format="docx", blocks=blocks)


# A slide title, when the deck has no title placeholder: the largest type on the slide, if it is at
# least this big and reads like words rather than a figure.
_TITLE_MIN_PT = 20.0
_TITLE_MAX_WORDS = 20


def _para_size(para) -> float | None:
    sizes = [r.font.size.pt for r in para.runs if r.text.strip() and r.font.size is not None]
    return max(sizes) if sizes else None


def _reads_like_words(text: str) -> bool:
    """'$2.4B' and '118%' are display figures, not titles; a title has at least two real words."""
    return sum(1 for w in re.findall(r"[A-Za-z]{2,}", text)) >= 2


def _composed_title(slide) -> tuple[int, float] | None:
    """(shape id, point size) of the paragraphs that title a slide built from plain text boxes.

    Decks generated in code (a slide library drawing every element as a text box) have no title
    placeholder, so without this every title reads as body copy: the heading rules never see one.
    The title is the largest type on the slide that reads like a short line of words.
    """
    best = None
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False) or not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            text = "".join(r.text for r in para.runs).strip()
            size = _para_size(para)
            if (size is None or size < _TITLE_MIN_PT or not _reads_like_words(text)
                    or word_count(text) > _TITLE_MAX_WORDS):
                continue
            if best is None or size > best[1]:
                best = (shape.shape_id, size)
    return best


def extract_pptx(path: Path) -> Document:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(str(path))
    blocks: list[Block] = []
    visuals: dict[int, int] = {}
    for s_no, slide in enumerate(prs.slides, 1):
        visuals[s_no] = sum(1 for sh in slide.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE
                            or getattr(sh, "has_chart", False))
        title_shape = slide.shapes.title
        has_title = title_shape is not None and bool(title_shape.text_frame.text.strip())
        composed = None if has_title else _composed_title(slide)
        for shape in slide.shapes:
            if getattr(shape, "has_table", False) and shape.has_table:
                for r_idx, row in enumerate(shape.table.rows, 1):
                    for c_idx, cell in enumerate(row.cells, 1):
                        text = re.sub(r"\s+", " ", cell.text).strip()
                        if text:
                            label = f"slide {s_no} table r{r_idx}c{c_idx}"
                            blocks.append(
                                Block(text=text, kind="table_cell", line=s_no, label=label, raw_lines=[(s_no, text)])
                            )
                continue
            if not getattr(shape, "has_text_frame", False) or not shape.has_text_frame:
                continue
            is_title = title_shape is not None and shape.shape_id == title_shape.shape_id
            for para in shape.text_frame.paragraphs:
                text = re.sub(r"\s+", " ", "".join(r.text for r in para.runs)).strip()
                if not text:
                    continue
                composed_title = (composed is not None and shape.shape_id == composed[0]
                                  and _para_size(para) == composed[1])
                if is_title or composed_title:
                    kind = "title"
                else:
                    kind = "list_item" if para.level > 0 else "paragraph"
                runs = [r for r in para.runs if r.text.strip()]
                bold_lead = bool(runs) and bool(runs[0].font.bold) and not all(bool(r.font.bold) for r in runs)
                blocks.append(
                    Block(
                        text=text,
                        kind=kind,
                        line=s_no,
                        label=f"slide {s_no}",
                        level=para.level,
                        bold_lead=bold_lead,
                        raw_lines=[(s_no, text)],
                    )
                )
        if slide.has_notes_slide:
            notes = re.sub(r"\s+", " ", slide.notes_slide.notes_text_frame.text).strip()
            if notes:
                blocks.append(Block(text=notes, kind="notes", line=s_no, label=f"slide {s_no} notes",
                                    raw_lines=[(s_no, notes)]))
    return Document(path=str(path), format="pptx", blocks=blocks, visuals=visuals)
