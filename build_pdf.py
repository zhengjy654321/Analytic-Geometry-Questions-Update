#!/usr/bin/env python3
"""一键按 outline.yaml 顺序将拆分后的 Markdown + 裁剪图合并排版为完整 PDF。

用法示例:
    python3 build_pdf.py                              # 合并全部模块 -> output/解析几何小题合集.pdf
    python3 build_pdf.py --modules 01                 # 仅合并模块 01（直线与方程）
    python3 build_pdf.py --modules 01,02 -o m12.pdf   # 指定输出文件名
    python3 build_pdf.py --html-only preview.html     # 仅导出排版后的自包含 HTML
"""

import argparse
import base64
import html
import mimetypes
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent


def encode_image_data_uri(img_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(img_path))
    if not mime:
        mime = "image/jpeg"
    data = base64.b64encode(img_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def parse_item_markdown(md_path: Path) -> dict:
    """解析单个知识点的 Markdown 文件，提取备注文字和按顺序排列的图片路径。"""
    text = md_path.read_text(encoding="utf-8")
    notes = []
    images = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if img_match:
            alt, rel = img_match.group(1), img_match.group(2)
            img_abs = (md_path.parent / rel).resolve()
            if img_abs.is_file():
                images.append((alt, img_abs))
        else:
            # 普通文字或勘误备注（支持 **粗体**）
            cleaned = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(line))
            notes.append(cleaned)

    return {"notes": notes, "images": images}


def build_html(outline_path: Path, selected_modules: set[str] | None = None) -> str:
    outline = yaml.safe_load(outline_path.read_text(encoding="utf-8"))
    doc_title = outline.get("title", "解析几何小题笔记合集")
    doc_subtitle = outline.get("subtitle", "")
    modules = outline.get("modules", [])

    if selected_modules:
        modules = [m for m in modules if str(m.get("id")) in selected_modules]

    if not modules:
        raise ValueError("未匹配到任何模块，请检查 --modules 参数或 outline.yaml。")

    # Build Table of Contents
    toc_blocks = []
    body_blocks = []

    for m_idx, mod in enumerate(modules, start=1):
        mod_id = f"mod-{mod['id']}"
        mod_title = html.escape(mod["title"])
        sub_toc_items = []

        body_blocks.append(f'<section class="module-section" id="{mod_id}">')
        body_blocks.append(
            f'<div class="module-banner">'
            f'<span class="module-tag">MODULE {html.escape(str(mod["id"]))}</span>'
            f'<h2>{mod_title}</h2>'
            f'</div>'
        )

        for s_idx, sub in enumerate(mod.get("subsections", []), start=1):
            sub_id = f"{mod_id}-sub-{s_idx}"
            sub_title = html.escape(sub["title"])
            item_count = len(sub.get("items", []))
            sub_toc_items.append(
                f'<li><a href="#{sub_id}">{sub_title}</a>'
                f'<span class="toc-meta">{item_count} 项</span></li>'
            )

            body_blocks.append(f'<h3 class="sub-heading" id="{sub_id}">{sub_title}</h3>')

            for i_idx, item in enumerate(sub.get("items", []), start=1):
                item_title = html.escape(item["title"])
                orig_num = html.escape(str(item.get("orig_num", "")))
                pages = html.escape(str(item.get("pages", "")))
                md_path = (outline_path.parent / item["file"]).resolve()
                parsed = parse_item_markdown(md_path)

                body_blocks.append('<article class="topic-block">')
                body_blocks.append(
                    f'<div class="topic-header">'
                    f'<span class="topic-title">{item_title}</span>'
                    f'<span class="topic-badge">原：{orig_num} ｜ {pages}</span>'
                    f'</div>'
                )
                for note_html in parsed["notes"]:
                    body_blocks.append(f'<div class="topic-note">{note_html}</div>')

                for alt, img_abs in parsed["images"]:
                    data_uri = encode_image_data_uri(img_abs)
                    body_blocks.append(
                        f'<figure class="note-figure">'
                        f'<img src="{data_uri}" alt="{html.escape(alt)}" />'
                        f'</figure>'
                    )
                body_blocks.append("</article>")

        body_blocks.append("</section>")

        toc_blocks.append(
            f'<div class="toc-module">'
            f'<div class="toc-module-title"><a href="#{mod_id}">{mod_title}</a></div>'
            f'<ul class="toc-sublist">{"".join(sub_toc_items)}</ul>'
            f'</div>'
        )

    total_items = sum(
        len(sub.get("items", []))
        for mod in modules
        for sub in mod.get("subsections", [])
    )
    mod_names = " · ".join(m["title"] for m in modules)

    return f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(doc_title)}</title>
  <style>
    :root {{
      --primary: #1e3a5f;
      --accent: #0f766e;
      --surface: #f8fafc;
      --surface-warm: #fffbeb;
      --border: #cbd5e1;
      --text: #1e293b;
      --muted: #475569;
      --bg: #ffffff;
    }}

    @page {{
      size: A4;
      margin: 16mm 15mm 18mm 15mm;
      background: var(--bg);
      @top-left {{
        content: "{html.escape(doc_title)}";
        font-family: 'Noto Sans CJK SC', 'Inter', sans-serif;
        font-size: 9pt;
        color: var(--muted);
      }}
      @bottom-right {{
        content: "第 " counter(page) " 页 / 共 " counter(pages) " 页";
        font-family: 'Noto Sans CJK SC', 'Inter', sans-serif;
        font-size: 9pt;
        color: var(--muted);
        white-space: nowrap;
      }}
    }}

    @page :first {{
      @top-left {{ content: none; }}
    }}

    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: transparent; }}
    body {{
      font-family: 'Noto Sans CJK SC', 'Inter', -apple-system, sans-serif;
      font-size: 11pt;
      line-height: 1.55;
      color: var(--text);
      letter-spacing: normal;
    }}

    @media screen {{
      html, body {{ background: #ffffff; }}
      body {{ max-width: 900px; margin: 0 auto; padding: 24px 32px; }}
    }}

    main.document-flow {{ width: 100%; }}

    /* Cover & TOC Header */
    .hero-header {{
      border-bottom: 3px solid var(--primary);
      padding-bottom: 14px;
      margin-bottom: 18px;
    }}
    .hero-kicker {{
      font-size: 9.5pt;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 4px;
    }}
    h1 {{
      font-size: 24pt;
      font-weight: 800;
      color: var(--primary);
      margin: 0 0 6px 0;
      line-height: 1.25;
    }}
    .hero-subtitle {{
      font-size: 11pt;
      color: var(--muted);
      margin: 0 0 8px 0;
    }}
    .hero-stats {{
      font-size: 10pt;
      color: var(--text);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      display: inline-block;
    }}

    .toc-box {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 22px;
    }}
    .toc-heading {{
      font-size: 13pt;
      font-weight: 700;
      color: var(--primary);
      margin: 0 0 10px 0;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--border);
    }}
    .toc-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
    }}
    .toc-module-title {{
      font-size: 11pt;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 6px;
    }}
    .toc-module-title a {{
      color: var(--primary);
      text-decoration: none;
    }}
    .toc-sublist {{
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .toc-sublist li {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      font-size: 10pt;
      padding: 3px 0;
      border-bottom: 1px dashed #e2e8f0;
    }}
    .toc-sublist a {{
      color: var(--text);
      text-decoration: none;
    }}
    .toc-meta {{
      font-size: 9.5pt;
      color: var(--muted);
      flex-shrink: 0;
      margin-left: 8px;
    }}

    /* Modules & Subsections */
    .module-section {{
      margin-top: 20px;
      break-inside: auto;
    }}
    .module-banner {{
      background: var(--primary);
      color: #ffffff;
      border-radius: 6px;
      padding: 10px 16px;
      margin: 18px 0 12px 0;
      break-after: avoid;
      page-break-after: avoid;
    }}
    .module-tag {{
      display: inline-block;
      font-size: 9pt;
      font-weight: 700;
      color: #bae6fd;
      margin-bottom: 2px;
    }}
    .module-banner h2 {{
      font-size: 16pt;
      font-weight: 700;
      color: #ffffff;
      margin: 0;
      padding: 0;
      border: none;
      line-height: 1.3;
    }}

    h3.sub-heading {{
      font-size: 13pt;
      font-weight: 700;
      color: var(--accent);
      margin: 16px 0 8px 0;
      padding-bottom: 4px;
      border-bottom: 1.5px solid #ccfbf1;
      break-after: avoid;
      page-break-after: avoid;
    }}

    /* Individual Topic Blocks */
    .topic-block {{
      margin: 0 0 14px 0;
      break-inside: auto;
    }}
    .topic-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 10px;
      background: var(--surface);
      border-left: 4px solid var(--primary);
      padding: 6px 10px;
      margin-bottom: 6px;
      border-radius: 0 4px 4px 0;
      break-after: avoid;
      page-break-after: avoid;
    }}
    .topic-title {{
      font-size: 11.5pt;
      font-weight: 700;
      color: var(--primary);
    }}
    .topic-badge {{
      font-size: 9.5pt;
      color: var(--muted);
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .topic-note {{
      font-size: 10pt;
      color: #92400e;
      background: var(--surface-warm);
      border-left: 3px solid #d97706;
      padding: 6px 10px;
      margin: 0 0 6px 0;
      border-radius: 0 4px 4px 0;
      break-inside: avoid;
      break-after: avoid;
    }}

    figure.note-figure {{
      margin: 0 0 8px 0;
      padding: 4px;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      background: #ffffff;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    figure.note-figure img {{
      display: block;
      width: 100%;
      max-height: 235mm;
      height: auto;
      object-fit: contain;
      margin: 0 auto;
    }}
  </style>
</head>
<body>
  <main class="document-flow">
    <header class="hero-header">
      <div class="hero-kicker">ANALYTIC GEOMETRY · 高考解析几何小题体系</div>
      <h1>{html.escape(doc_title)}</h1>
      <p class="hero-subtitle">{html.escape(doc_subtitle)}</p>
      <div class="hero-stats">收录范围：{html.escape(mod_names)}（共 {total_items} 个知识点）</div>
    </header>

    <nav class="toc-box">
      <div class="toc-heading">目录导航</div>
      <div class="toc-grid">
        {"".join(toc_blocks)}
      </div>
    </nav>

    {"".join(body_blocks)}
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="按 outline.yaml 自动合并排版解析几何小题笔记为 PDF")
    parser.add_argument("--outline", default=str(REPO_ROOT / "outline.yaml"), help="outline.yaml 路径")
    parser.add_argument("--modules", default="", help="仅合并指定模块编号，如 01 或 01,02（默认合并全部）")
    parser.add_argument("-o", "--output", default=str(REPO_ROOT / "output" / "解析几何小题合集.pdf"), help="输出 PDF 路径")
    parser.add_argument("--html-only", default="", help="仅输出自包含 HTML 文件路径，不调用 WeasyPrint")
    args = parser.parse_args()

    selected = {m.strip().zfill(2) for m in args.modules.split(",") if m.strip()} or None
    html_str = build_html(Path(args.outline), selected)

    if args.html_only:
        out_html = Path(args.html_only)
        out_html.parent.mkdir(parents=True, exist_ok=True)
        out_html.write_text(html_str, encoding="utf-8")
        print(f"已导出 HTML：{out_html}")
        return

    try:
        from weasyprint import HTML
    except ImportError:
        print("未安装 weasyprint，请先运行：pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    out_pdf = Path(args.output)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str, base_url=str(REPO_ROOT)).write_pdf(str(out_pdf))
    print(f"已生成合并 PDF：{out_pdf} ({out_pdf.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
