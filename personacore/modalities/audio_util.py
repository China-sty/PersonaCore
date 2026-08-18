"""音频转码工具：把各种音频格式转成 DashScope 实时识别需要的 PCM 16kHz。"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def convert_to_pcm16k(audio: bytes) -> bytes:
    """用 ffmpeg 把任意音频转成 PCM s16le 16kHz 单声道。

    依赖系统命令 ffmpeg（未安装会抛出明确错误）。
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("未安装 ffmpeg，无法转码音频。请先安装：apt-get install -y ffmpeg")

    with tempfile.NamedTemporaryFile(suffix=".in", delete=False) as src:
        src.write(audio)
        src_path = Path(src.name)

    dst_path = src_path.with_suffix(".pcm")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src_path),
                "-ar", "16000", "-ac", "1", "-f", "s16le", "-acodec", "pcm_s16le",
                str(dst_path),
            ],
            check=True, capture_output=True,
        )
        return dst_path.read_bytes()
    finally:
        src_path.unlink(missing_ok=True)
        dst_path.unlink(missing_ok=True)
