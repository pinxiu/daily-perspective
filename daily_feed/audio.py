"""Narrate the daily briefing to MP3 with Kokoro, an open-source neural TTS model.

Runs on the GitHub Actions CPU in a few minutes and costs nothing. Produces
docs/audio/<date>-en.mp3 and docs/audio/<date>-zh.mp3, plus the start time of
every section and story so the page can jump straight to one.

Any failure here is logged and skipped: the page then falls back to the
browser's built-in voice.
"""
from __future__ import annotations

import os
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
MODELS = {
    "en": ("kokoro-v1.0.fp16.onnx", "voices-v1.0.bin"),
    "zh": ("kokoro-v1.1-zh.fp16.onnx", "voices-v1.1-zh.bin"),
}
DEFAULT_VOICES = {"en": "af_heart", "zh": "zf_001"}
KEEP_DAYS = 30          # older audio is deleted to keep the site small
BITRATE = 32            # kbps, mono: clear for speech, ~4 MB per 15 minutes
SAMPLE_RATE = 24000
PAUSE_ITEM, PAUSE_SECTION = 0.45, 1.0   # seconds of silence between stories / sections

CACHE = Path(os.environ.get("KOKORO_CACHE") or Path.home() / ".cache" / "kokoro")


def _download(name: str) -> Path:
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f"  downloading {name}")
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URL + name, tmp)
        tmp.rename(path)
    return path


def _segments(reflection: str, sections: list[dict], lang: str) -> list[tuple[str, str, float]]:
    """(anchor id, text, pause before) in reading order."""
    zh = lang == "zh"
    out: list[tuple[str, str, float]] = []
    r = reflection
    if r:
        out.append(("top", r, 0.0))
    for si, s in enumerate(sections):
        name = (s.get("name_zh") if zh else "") or s["name"]
        overview = s.get("overview_zh", "") if zh else s["overview"]
        intro = f"{name}。{overview}" if zh else f"{name}. {overview}"
        out.append((s["id"], intro, PAUSE_SECTION if out else 0.0))
        for ti, st in enumerate(s["stories"]):
            if zh:
                title = st.get("title_zh", "")
                parts = [title and title + "。", st.get("why_it_matters_zh", ""), st.get("perspective_zh", "")]
                text = "".join(p for p in parts if p)
            else:
                text = " ".join(p for p in (st["item"].title.rstrip(".") + ".", st["why_it_matters"],
                                            st["perspective"]) if p)
            if text:
                out.append((f"s{si}-{ti}", text, PAUSE_ITEM))
    return out


class Narrator:
    def __init__(self, voices: dict[str, str] | None = None) -> None:
        self.voices = {**DEFAULT_VOICES, **(voices or {})}
        self._models: dict = {}
        self._g2p = None

    def _model(self, lang: str):
        if lang not in self._models:
            from kokoro_onnx import Kokoro

            model, voices = (_download(n) for n in MODELS[lang])
            self._models[lang] = Kokoro(str(model), str(voices))
        return self._models[lang]

    def _speak(self, text: str, lang: str):
        import numpy as np

        kokoro, voice = self._model(lang), self.voices[lang]
        if lang == "zh":
            if self._g2p is None:
                from misaki import zh

                self._g2p = zh.ZHG2P(version="1.1")
            clips = []
            # Phonemize sentence by sentence; long inputs lose their prosody.
            for sent in re.findall(r"[^。！？!?]+[。！？!?]?", text):
                if sent.strip():
                    phonemes, _ = self._g2p(sent.strip())
                    audio, _ = kokoro.create(phonemes, voice=voice, is_phonemes=True)
                    clips.append(audio)
            return np.concatenate(clips) if clips else np.zeros(0, dtype=np.float32)
        audio, _ = kokoro.create(text, voice=voice, lang="en-us")
        return audio

    def narrate(self, reflection: str, sections: list[dict], lang: str) -> tuple[bytes, dict[str, float]]:
        """MP3 bytes and {anchor id: start seconds}."""
        import lameenc
        import numpy as np

        pcm, offsets, t = [], {}, 0.0
        for anchor, text, pause in _segments(reflection, sections, lang):
            if pause:
                pcm.append(np.zeros(int(pause * SAMPLE_RATE), dtype=np.float32))
                t += pause
            offsets[anchor] = round(t, 2)
            clip = self._speak(text, lang)
            pcm.append(clip)
            t += len(clip) / SAMPLE_RATE
        samples = (np.clip(np.concatenate(pcm), -1, 1) * 32767).astype("<i2")
        enc = lameenc.Encoder()
        enc.set_bit_rate(BITRATE)
        enc.set_in_sample_rate(SAMPLE_RATE)
        enc.set_channels(1)
        enc.set_quality(2)
        return enc.encode(samples.tobytes()) + enc.flush(), offsets


def build_audio(docs: Path, day: date, reflection: str, reflection_zh: str,
                sections: list[dict], voices: dict[str, str] | None = None) -> dict:
    """Write today's MP3s; returns {lang: {"file": relative path, "at": offsets}}."""
    if os.environ.get("AUDIO", "1") == "0":
        return {}
    audio_dir = docs / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    _prune(audio_dir, day)
    narrator = Narrator(voices)
    result = {}
    for lang, refl in (("en", reflection), ("zh", reflection_zh)):
        if lang == "zh" and not any(s.get("overview_zh") for s in sections):
            continue   # no translation today: don't narrate a half-English "Chinese" track
        try:
            mp3, offsets = narrator.narrate(refl, sections, lang)
        except Exception as e:
            print(f"  ! {lang} narration failed: {e}")
            continue
        name = f"{day.isoformat()}-{lang}.mp3"
        (audio_dir / name).write_bytes(mp3)
        result[lang] = {"file": f"audio/{name}", "at": offsets}
        print(f"  narrated {lang}: {max(offsets.values(), default=0) / 60:.1f}+ min, {len(mp3) // 1024} KB")
    return result


def _prune(audio_dir: Path, today: date) -> None:
    cutoff = today - timedelta(days=KEEP_DAYS)
    for f in audio_dir.glob("*.mp3"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-", f.name)
        if m and date.fromisoformat(m.group(1)) < cutoff:
            f.unlink()
