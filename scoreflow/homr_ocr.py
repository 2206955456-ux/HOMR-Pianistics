# -*- coding: utf-8 -*-
"""第二步：调用 HOMR 逐页识别 PNG -> MusicXML

HOMR 以子进程方式调用其发行版自带的嵌入式 Python（python_embed）。
注意：必须以 homr 主目录为工作目录运行，模型权重（*.onnx）放在
homr/segmentation 与 homr/transformer 目录下，工作目录不对会找不到权重。
"""

import subprocess
import sys
from pathlib import Path


def recognize_image(homr_python: Path, homr_dir: Path, image: Path,
                    gpu: str = "no", timeout: int = 600) -> Path:
    """识别单页，返回生成的 MusicXML 路径（与图片同目录同名）。"""
    cmd = [
        str(homr_python), "-m", "homr.main",
        str(image), "--gpu", gpu,
    ]
    result = subprocess.run(
        cmd,
        cwd=str(homr_dir),          # 关键：权重相对 homr 主目录解析
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    xml_path = image.with_suffix(".musicxml")
    if result.returncode != 0 or not xml_path.exists():
        detail = (result.stderr or result.stdout or "")[-600:]
        raise HomrError(f"HOMR 识别失败: {image.name}\n{detail}")
    return xml_path


def recognize_pages(homr_python: Path, homr_dir: Path, images: list[Path],
                    gpu: str = "no", timeout: int = 600,
                    log=print) -> list[Path]:
    """逐页识别，返回成功的 MusicXML 列表；单页失败不中断整体。"""
    xml_files = []
    for i, img in enumerate(images, 1):
        log(f"  [{i}/{len(images)}] 识别 {img.name} ...")
        try:
            xml_files.append(recognize_image(homr_python, homr_dir, img, gpu, timeout))
        except subprocess.TimeoutExpired:
            log(f"    ✗ 超时（>{timeout}s），跳过")
        except HomrError as e:
            log(f"    ✗ {e}")
    return xml_files


class HomrError(Exception):
    pass
