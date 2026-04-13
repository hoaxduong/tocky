import asyncio
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".aac"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def validate_audio_file(filename: str, size: int) -> None:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if size > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large ({size / 1024 / 1024:.1f} MB). "
            f"Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB."
        )


async def convert_to_pcm(input_bytes: bytes) -> bytes:
    """Convert audio bytes to PCM 16kHz 16-bit mono using ffmpeg."""
    logger.debug("convert_to_pcm: input=%d bytes", len(input_bytes))
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=input_bytes)
    if proc.returncode != 0:
        err = stderr.decode(errors="replace")
        logger.error("ffmpeg failed (rc=%d): %s", proc.returncode, err[:500])
        raise RuntimeError(f"ffmpeg conversion failed: {err[:500]}")
    duration_s = len(stdout) / 32000  # 16kHz * 2 bytes
    logger.debug(
        "convert_to_pcm: output=%d bytes (%.1fs audio)",
        len(stdout),
        duration_s,
    )
    return stdout
