"""语音情绪识别：可插拔接口。

信号统一结构（dict）：
    {"emotion": str, "confidence": float}
其中 emotion 为情绪标签（如 平静/紧张/愤怒/悲伤/中性…），confidence 为 0~1。
"""
from __future__ import annotations

import abc
import tempfile
from pathlib import Path

from .audio_util import convert_to_wav16k

_EN2ZH = {
    "angry": "生气", "disgust": "厌恶", "fear": "恐惧", "happy": "开心",
    "neutral": "中性", "other": "其他", "sad": "悲伤", "surprise": "惊喜",
}


class EmotionRecognizer(abc.ABC):
    """从音频字节识别情绪，返回信号 dict 或 None（无模型/无法识别）。"""

    @abc.abstractmethod
    def recognize(self, audio: bytes, sample_rate: int = 16000) -> dict | None:
        raise NotImplementedError


class NullEmotionRecognizer(EmotionRecognizer):
    """空实现：不识别情绪，返回 None。"""

    def recognize(self, audio: bytes, sample_rate: int = 16000) -> dict | None:
        return None


class Emotion2vecRecognizer(EmotionRecognizer):
    """emotion2vec（阿里 FunAudioLLM）情绪识别，从 ModelScope 加载。

    依赖 funasr / modelscope / torch（见 requirements-audio.txt）。
    首次调用会懒加载模型（较慢），后续复用；识别失败返回 None，不阻断面试。
    """

    def __init__(self, model_name: str = "iic/emotion2vec_plus_base"):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from funasr import AutoModel
            self._model = AutoModel(model=self.model_name)
        return self._model

    def recognize(self, audio: bytes, sample_rate: int = 16000) -> dict | None:
        try:
            model = self._load()
            wav = convert_to_wav16k(audio)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav)
                wav_path = f.name
            try:
                res = model.generate(input=wav_path)
            finally:
                Path(wav_path).unlink(missing_ok=True)
            return self._parse(res)
        except Exception:
            # 情绪识别失败不阻断面试
            return None

    def _parse(self, res) -> dict | None:
        label: str | None = None
        score: float = 0.0
        try:
            r = res[0] if isinstance(res, list) and res else res
            if isinstance(r, dict):
                labels = r.get("labels")
                scores = r.get("scores")
                if isinstance(labels, str):
                    label = labels
                    score = float(scores[0]) if isinstance(scores, list) and scores else float(scores or 0)
                elif isinstance(labels, list) and isinstance(scores, list) and len(labels) == len(scores):
                    idx = max(range(len(scores)), key=lambda i: scores[i])
                    label, score = labels[idx], float(scores[idx])
                elif r.get("outputs"):
                    out = r["outputs"][0]
                    label = out.get("label")
                    score = float(out.get("score", 0))
        except Exception:
            return None

        if not label:
            return None
        return {"emotion": _EN2ZH.get(label, label), "confidence": round(score, 3)}
