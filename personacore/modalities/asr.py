"""语音转文字（ASR）：可插拔接口。"""
from __future__ import annotations

import abc
import os

from .audio_util import convert_to_pcm16k


class Transcriber(abc.ABC):
    """把音频字节转成文字。"""

    @abc.abstractmethod
    def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        raise NotImplementedError


class DashscopeTranscriber(Transcriber):
    """阿里云 DashScope Paraformer 实时识别（WebSocket 流式）。

    流程：ffmpeg 转 PCM16k → 分帧喂给 Recognition → 汇总文字。
    需要环境变量 DASHSCOPE_API_KEY。
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("未配置 DASHSCOPE_API_KEY，无法使用语音转文字")

    def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        import dashscope
        from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

        dashscope.api_key = self.api_key
        pcm = convert_to_pcm16k(audio)

        sentences: list[str] = []

        class _Callback(RecognitionCallback):
            def on_event(self, result):
                sentence = result.get_sentence() if isinstance(result, RecognitionResult) else None
                if not sentence:
                    return
                text = sentence.get("text") if isinstance(sentence, dict) else getattr(sentence, "text", None)
                if text:
                    sentences.append(text)

        recognition = Recognition(
            model="paraformer-realtime-v2",
            format="pcm",
            sample_rate=16000,
            callback=_Callback(),
        )
        recognition.start()
        try:
            chunk = 3200  # ~100ms @ 16kHz 16bit
            for i in range(0, len(pcm), chunk):
                recognition.send_audio_frame(pcm[i : i + chunk])
        finally:
            recognition.stop()

        return "".join(sentences).strip()


class MockTranscriber(Transcriber):
    """测试用：固定返回一段文字。"""

    def __init__(self, text: str = "（测试转写文本）"):
        self.text = text

    def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        return self.text
