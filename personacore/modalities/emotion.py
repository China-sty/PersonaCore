"""语音情绪识别：可插拔接口。

信号统一结构（dict）：
    {"emotion": str, "confidence": float}
其中 emotion 为情绪标签（如 平静/紧张/愤怒/悲伤/中性…），confidence 为 0~1。
"""
from __future__ import annotations

import abc


class EmotionRecognizer(abc.ABC):
    """从音频字节识别情绪，返回信号 dict 或 None（无模型/无法识别）。"""

    @abc.abstractmethod
    def recognize(self, audio: bytes, sample_rate: int = 16000) -> dict | None:
        raise NotImplementedError


class NullEmotionRecognizer(EmotionRecognizer):
    """空实现：Phase 2.1 暂不识别情绪，返回 None。"""

    def recognize(self, audio: bytes, sample_rate: int = 16000) -> dict | None:
        return None


class Emotion2vecRecognizer(EmotionRecognizer):
    """emotion2vec（阿里 FunAudioLLM）情绪识别。Phase 2.2 接入。

    依赖：funasr / modelscope / torch（见 requirements-audio.txt），模型从 ModelScope 下载。
    """

    def recognize(self, audio: bytes, sample_rate: int = 16000) -> dict | None:
        # TODO(2.2): 懒加载 emotion2vec 模型，对音频做情绪分类
        raise NotImplementedError(
            "emotion2vec 待接入（Phase 2.2）：需先安装 requirements-audio.txt 并下载模型。"
        )
