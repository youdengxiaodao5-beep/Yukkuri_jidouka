#!/usr/bin/env python3

# Minimal safe implementation to:
# - call VOICEVOX local API to synthesize speech
# - create a video from a background image (optionally overlay a character)
# - mux audio and video using ffmpeg (no shell=True)
from __future__ import annotations
import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
DEFAULT_VOICEVox_HOST = os.environ.get("VOICEVOX_HOST", "127.0.0.1")
DEFAULT_VOICEVox_PORT = int(os.environ.get("VOICEVOX_PORT", "50021"))
DEFAULT_VOICE_ID = int(os.environ.get("VOICE_ID", "1"))
# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("yukkuri")
def make_session(timeout: int = 10) -> requests.Session:
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3, status_forcelist=(500, 502, 504))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.request = lambda *args, **kwargs: requests.Session.request(s, *args, timeout=timeout, **kwargs)
    return s
def voicevox_audio_query(session: requests.Session, host: str, port: int, text: str, speaker: int) -> dict:
    url = f"http://{host}:{port}/audio_query"
    params = {"text": text, "speaker": speaker}
    logger.debug("Requesting audio_query: %s %s", url, params)
    resp = session.post(url, params=params)
    resp.raise_for_status()
    return resp.json()
def voicevox_synthesis(session: requests.Session, host: str, port: int, audio_query: dict, speaker: int) -> bytes:
    url = f"http://{host}:{port}/synthesis"
    params = {"speaker": speaker}
    headers = {"Content-Type": "application/json"}
    logger.debug("Requesting synthesis: %s", url)
    resp = session.post(url, params=params, json=audio_query, headers=headers)
    resp.raise_for_status()
    return resp.content
def save_wav_bytes(wav_bytes: bytes, prefix: str = "yukkuri") -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=".wav")
    tmp.write(wav_bytes)
    tmp.flush()
    tmp.close()
    p = Path(tmp.name)
    logger.info("Saved synthesized wav to %s", p)
    return p
def get_wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        return frames / float(rate)
def check_ffmpeg() -> Optional[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.error("ffmpeg not found in PATH. Please install ffmpeg and ensure it's on PATH.")
        return None
    return ffmpeg
def build_ffmpeg_cmd(
    ffmpeg_cmd: str,
    bg_path: Path,
    audio_path: Path,
    out_path: Path,
    char_path: Optional[Path] = None,
) -> list[str]:
    cmd = [ffmpeg_cmd, "-y", "-loop", "1", "-i", str(bg_path)]
    if char_path:
        cmd += ["-i", str(char_path)]
    cmd += ["-i", str(audio_path)]
    if char_path:
        filter_complex = "[0:v][1:v] overlay=W-w-10:H-h-10,format=yuv420p"
        cmd += ["-filter_complex", filter_complex]
    else:
        cmd += ["-vf", "format=yuv420p"]
    cmd += [
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out_path)
    ]
    logger.debug("FFmpeg command: %s", " ".join(cmd))
    return cmd
def run_ffmpeg(cmd: list[str]) -> None:
    logger.info("Running ffmpeg...")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        logger.error("ffmpeg failed (rc=%d): %s", proc.returncode, proc.stderr)
        raise RuntimeError("ffmpeg failed, see log")
    logger.info("ffmpeg completed successfully")
def ensure_out_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a yukkuri-like video using VOICEVOX")
    ap.add_argument("topic", help="トピック文字列（字幕・音声に使う）")
    ap.add_argument("--voice-id", type=int, default=DEFAULT_VOICE_ID, help="VOICEVOX の speaker id")
    ap.add_argument("--voicevox-host", default=DEFAULT_VOICEVox_HOST, help="VOICEVOX ホスト")
    ap.add_argument("--voicevox-port", type=int, default=DEFAULT_VOICEVox_PORT, help="VOICEVOX ポート")
    ap.add_argument("--background", required=True, help="背景画像パス（例: assets/background.png）")
    ap.add_argument("--char", help="立ち絵画像パス（任意）")
    ap.add_argument("--out", default="out/result.mp4", help="出力 MP4 パス")
    args = ap.parse_args()
    bg_path = Path(args.background)
    if not bg_path.exists():
        logger.error("background image not found: %s", bg_path)
        return 2
    char_path = Path(args.char) if args.char else None
    if char_path and not char_path.exists():
        logger.error("char image not found: %s", char_path)
        return 2
    ffmpeg_cmd = check_ffmpeg()
    if not ffmpeg_cmd:
        return 3
    session = make_session()
    try:
        aq = voicevox_audio_query(session, args.voicevox_host, args.voicevox_port, args.topic, args.voice_id)
        wav_bytes = voicevox_synthesis(session, args.voicevox_host, args.voicevox_port, aq, args.voice_id)
    except Exception as e:
        logger.exception("Failed to synthesize audio: %s", e)
        return 4
    audio_path = save_wav_bytes(wav_bytes)
    try:
        duration = get_wav_duration_seconds(audio_path)
        logger.info("Audio duration: %.2f seconds", duration)
    except Exception:
        logger.warning("Failed to get audio duration; continuing anyway")
    out_path = Path(args.out)
    ensure_out_dir(out_path)
    cmd = build_ffmpeg_cmd(ffmpeg_cmd, bg_path, audio_path, out_path, char_path)
    try:
        run_ffmpeg(cmd)
    finally:
        logger.info("Generated video: %s", out_path)
    return 0
if __name__ == "__main__":
    sys.exit(main())
