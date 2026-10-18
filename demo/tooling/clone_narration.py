#!/usr/bin/env python3
"""Local OpenVoice V2 scene conversion. Does not upload samples or call an API.

Run with tmp/voice-tools/venv/Scripts/python.exe after setup_voice.ps1.
Converter mathematics adapt OpenVoice's MIT-licensed api.py; upstream model
modules and license stay in ignored tmp/voice-tools/OpenVoice.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
PRIVATE = REPO / "tmp"
TOOLS = PRIVATE / "voice-tools"
SOURCE_REVISION = "74a1d147b17a8c3092dd5430504bd83ef6c7eb23"
MODEL_REVISION = "f36e7edfe1684461a8343844af60babc2efbb727"


def private_output(value: str | Path) -> Path:
    destination = Path(value).expanduser().resolve()
    if not destination.is_relative_to(PRIVATE.resolve()):
        raise ValueError("Voice outputs must stay below this repository's ignored tmp directory.")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Output directory already contains files; choose a new directory to preserve them.")
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def local_file(value: str | Path) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Local input file does not exist: {path.name}")
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("A voice input exceeds the 100 MB local limit.")
    return path


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def get_ffmpeg(override: str | None) -> Path:
    result = Path(override).resolve() if override else REPO / "demo/tooling/node_modules/ffmpeg-static/ffmpeg.exe"
    if not result.is_file():
        raise ValueError("FFmpeg was not found. Supply --ffmpeg with an existing local executable.")
    return result


def decode(path: Path, ffmpeg: Path, rate: int, np, limit: float = 180):
    command = [str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error",
               "-protocol_whitelist", "file,pipe", "-i", str(path), "-t", str(limit),
               "-vn", "-ac", "1", "-ar", str(rate), "-f", "f32le", "pipe:1"]
    result = subprocess.run(command, capture_output=True, check=False, timeout=90)
    if result.returncode:
        raise ValueError(f"Could not decode {path.name}: {result.stderr.decode(errors='replace')[-600:]}")
    audio = np.frombuffer(result.stdout, dtype="<f4").copy()
    if len(audio) < rate or not np.isfinite(audio).all():
        raise ValueError(f"{path.name} has less than one second of usable finite audio.")
    return audio


def audio_metrics(audio, rate: int, np) -> dict:
    return {"duration_seconds": round(len(audio) / rate, 3),
            "peak": round(float(np.max(np.abs(audio))), 5),
            "rms": round(float(np.sqrt(np.mean(audio ** 2))), 5),
            "clipped_fraction": round(float(np.mean(np.abs(audio) >= 0.999)), 6)}


def reference_segments(audio, rate: int, np) -> list:
    # No speech-recognition/VAD model is downloaded. Exclude quiet windows and
    # take multiple bounded segments; the user should supply clean solo speech.
    frame = int(rate * .05)
    chunks = [audio[pos:pos + frame] for pos in range(0, len(audio), frame)]
    energy = np.array([np.sqrt(np.mean(chunk ** 2)) for chunk in chunks])
    threshold = max(0.002, float(np.max(energy)) * 0.025)
    voiced = np.flatnonzero(energy > threshold)
    if len(voiced) * .05 < 3:
        raise ValueError("Need at least three seconds of clear speech for a reference embedding.")
    begin = max(0, int(voiced[0]) * frame - int(.15 * rate))
    end = min(len(audio), (int(voiced[-1]) + 1) * frame + int(.15 * rate))
    audio = audio[begin:end]
    result = []
    for pos in range(0, len(audio), 10 * rate):
        chunk = audio[pos:pos + 10 * rate]
        if len(chunk) >= 3 * rate and float(np.sqrt(np.mean(chunk ** 2))) > threshold:
            result.append(chunk)
    if not result:
        raise ValueError("No sufficiently long clean reference segment was found.")
    return result[:9]


class Converter:
    def __init__(self, np, torch, threads: int):
        self.np, self.torch = np, torch
        torch.set_num_threads(threads)
        torch.manual_seed(17)
        manifest_file = TOOLS / "model-manifest.json"
        if not manifest_file.is_file():
            raise ValueError("Run demo/tooling/setup_voice.ps1 to prepare the isolated voice tools.")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
        if manifest.get("source_revision") != SOURCE_REVISION or manifest.get("model_revision") != MODEL_REVISION:
            raise ValueError("Voice model/source revision does not match the reviewed fixed revisions.")
        checkpoint = TOOLS / "converter/checkpoint.pth"
        if digest(checkpoint) != manifest.get("checkpoint_sha256"):
            raise ValueError("Voice checkpoint digest does not match the verified model manifest.")
        config = json.loads((TOOLS / "converter/config.json").read_text(encoding="utf-8-sig"))
        sys.path.insert(0, str(TOOLS / "OpenVoice"))
        from openvoice.models import SynthesizerTrn
        self.data = config["data"]
        self.rate = self.data["sampling_rate"]
        self.model = SynthesizerTrn(0, self.data["filter_length"] // 2 + 1,
                                    n_speakers=self.data["n_speakers"], **config["model"]).cpu().eval()
        checkpoint_data = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.model.load_state_dict(checkpoint_data["model"], strict=True)
        self.window = torch.hann_window(self.data["win_length"])
        self.manifest = manifest

    def spectrogram(self, audio):
        torch = self.torch
        y = torch.from_numpy(self.np.array(audio, dtype=self.np.float32, copy=True)).unsqueeze(0)
        padding = (self.data["filter_length"] - self.data["hop_length"]) // 2
        y = torch.nn.functional.pad(y.unsqueeze(1), (padding, padding), mode="reflect").squeeze(1)
        spec = torch.stft(y, self.data["filter_length"], hop_length=self.data["hop_length"],
                          win_length=self.data["win_length"], window=self.window,
                          center=False, pad_mode="reflect", normalized=False,
                          onesided=True, return_complex=True)
        return self.torch.sqrt(spec.real.square() + spec.imag.square() + 1e-6)

    def embedding(self, audio):
        with self.torch.inference_mode():
            embeddings = [self.model.ref_enc(self.spectrogram(part).transpose(1, 2)).unsqueeze(-1)
                          for part in reference_segments(audio, self.rate, self.np)]
            return self.torch.stack(embeddings).mean(0)

    def convert(self, audio, source_embedding, target_embedding, tau: float):
        with self.torch.inference_mode():
            spec = self.spectrogram(audio)
            lengths = self.torch.tensor([spec.size(-1)], dtype=self.torch.long)
            converted = self.model.voice_conversion(spec, lengths, sid_src=source_embedding,
                                                    sid_tgt=target_embedding, tau=tau)[0][0, 0]
            output = converted.cpu().float().numpy()
        if not self.np.isfinite(output).all():
            raise ValueError("Conversion produced non-finite audio.")
        return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", required=True, help="Local solo voice recording; no upload occurs.")
    parser.add_argument("--source-dir", default=str(PRIVATE / "submission-audio"))
    parser.add_argument("--script", default=str(REPO / "demo/tooling/submission_script.json"))
    parser.add_argument("--scene", default="intro", help="Preview scene ID (default: intro).")
    parser.add_argument("--all-scenes", action="store_true", help="Convert all scene WAVs after reviewing a preview.")
    parser.add_argument("--preview-seconds", type=float, default=12)
    parser.add_argument("--output-dir", default=str(PRIVATE / "voice-output" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")))
    parser.add_argument("--ffmpeg")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--tau", type=float, default=.3)
    parser.add_argument("--synthetic-test", action="store_true", help="Label test proof as synthetic, never as the user's voice.")
    args = parser.parse_args()
    if not 1 <= args.threads <= 16 or not 0 <= args.tau <= 1 or not 3 <= args.preview_seconds <= 30:
        parser.error("Use 1-16 threads, tau 0-1 and preview length 3-30 seconds.")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    import numpy as np
    import soundfile as sf
    import torch

    sample = local_file(args.sample)
    script = json.loads(local_file(args.script).read_text(encoding="utf-8-sig"))
    ids = [scene["id"] for scene in script]
    if not ids or len(set(ids)) != len(ids) or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", name) for name in ids):
        raise ValueError("Scene IDs must be unique safe filenames.")
    if args.scene not in ids:
        raise ValueError("Preview scene was not found in the scene script.")
    chosen = ids if args.all_scenes else [args.scene]
    sources = {name: local_file(Path(args.source_dir) / f"{name}.wav") for name in chosen}
    output = private_output(args.output_dir)
    ffmpeg = get_ffmpeg(args.ffmpeg)
    start = time.monotonic()
    converter = Converter(np, torch, args.threads)
    target_audio = decode(sample, ffmpeg, converter.rate, np)
    source_reference = decode(sources[chosen[0]], ffmpeg, converter.rate, np)
    sample_metrics = audio_metrics(target_audio, converter.rate, np)
    reference_gain = min(1.0, .95 / max(float(np.max(np.abs(target_audio))), 1e-8))
    target_audio = target_audio * reference_gain
    if sample_metrics["clipped_fraction"] > .01:
        print("Warning: more than 1% of reference audio clips; a cleaner recording may improve quality.")
    shutil.copy2(sample, output / ("reference-original" + sample.suffix.lower()))
    sf.write(output / "reference-decoded.wav", target_audio, converter.rate, subtype="PCM_16")
    target_se = converter.embedding(target_audio)
    source_se = converter.embedding(source_reference)
    torch.save(target_se, output / "target-embedding.pt")
    torch.save(source_se, output / "source-embedding.pt")
    report = {"status": "running", "proof_kind": "synthetic_pipeline_test" if args.synthetic_test else "local_voice_reference_conversion",
              "disclosure": "AI-assisted narration using the supplied reference voice; tone similarity requires listening review.",
              "paid_api_calls": 0, "voice_uploads": 0, "device": "cpu", "sample_metrics": sample_metrics,
              "reference_gain": round(reference_gain, 6), "model": converter.manifest, "python": sys.version.split()[0], "threads": args.threads,
              "packages": {name: metadata.version(name) for name in ["torch", "numpy", "soundfile"]},
              "outputs": []}
    narration = []
    text_by_id = {scene['id']: scene['text'] for scene in script}
    for name, source in sources.items():
        audio = decode(source, ffmpeg, converter.rate, np, limit=90)
        if not args.all_scenes:
            audio = audio[:int(args.preview_seconds * converter.rate)]
        scene_start = time.monotonic()
        converted = converter.convert(audio, source_se, target_se, args.tau)
        path = output / f"{name}.wav"
        sf.write(path, converted, converter.rate, subtype="PCM_16")
        metrics = audio_metrics(converted, converter.rate, np)
        if metrics["rms"] < .0001 or abs(len(converted) - len(audio)) / converter.rate > .25:
            raise ValueError(f"Converted scene {name} failed audio energy/duration checks.")
        elapsed = round(time.monotonic() - scene_start, 3)
        report["outputs"].append({"scene": name, "file": path.name, "sha256": digest(path),
                                  "metrics": metrics, "conversion_seconds": elapsed})
        narration.append({'id': name, 'text': text_by_id[name], 'audio': str(path.resolve()), 'durationMs': round(len(converted) / converter.rate * 1000)})
        print(f"Converted {name}: {metrics['duration_seconds']} seconds of audio in {elapsed} seconds", flush=True)
    (output / 'converted-scenes.json').write_text(json.dumps(narration, indent=2) + '\n', encoding='utf-8')
    report["status"] = "pipeline_verified_listening_review_required"
    report["total_seconds"] = round(time.monotonic() - start, 3)
    (output / "voice-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Private output: {output.relative_to(REPO)}")
    print("Synthetic pipeline proof only; no user voice was used." if args.synthetic_test else "Review the preview before using the converted voice in a final video.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"Voice conversion failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
