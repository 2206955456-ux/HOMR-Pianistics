# -*- coding: utf-8 -*-
"""第一步：PDF -> 每页 PNG（pypdfium2 渲染）"""

from pathlib import Path

import pypdfium2 as pdfium


def render_pdf(pdf_path: Path, out_dir: Path, dpi: int = 300) -> list[Path]:
    """把 PDF 渲染成每页一张 PNG，返回图片路径列表（按页序）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        scale = dpi / 72.0
        images = []
        for i in range(len(doc)):
            page = doc[i]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            img_path = out_dir / f"page_{i + 1:03d}.png"
            pil_image.save(img_path)
            images.append(img_path)
        return images
    finally:
        doc.close()
