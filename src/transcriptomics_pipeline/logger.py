from __future__ import annotations

import logging
import re
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DEFAULT_LOG_FILE = "sample_log.txt"


def configure_file_logger(log_path: Path, append: bool = False) -> logging.Logger:
    logger = logging.getLogger("transcriptomics_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    mode = "a" if append else "w"
    handler = logging.FileHandler(log_path, mode=mode, encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def human_readable_size(size: int) -> str:
    for unit in ["bytes", "KiB", "MiB", "GiB", "TiB"]:
        if size < 1024 or unit == "TiB":
            if unit == "bytes":
                return f"{size} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TiB"


def log_sample_success(
    logger: logging.Logger,
    accession: str,
    files: list[Path],
    backend: str,
) -> None:
    for file_path in files:
        size = file_path.stat().st_size
        logger.info(
            "SUCCESS accession=%s backend=%s path=%s size=%s",
            accession,
            backend,
            file_path.resolve(),
            human_readable_size(size),
        )


def log_sample_failure(logger: logging.Logger, accession: str, backend: str, error: Exception) -> None:
    logger.error(
        "FAIL accession=%s backend=%s error=%s",
        accession,
        backend,
        error,
    )


def log_batch_summary(logger: logging.Logger, total: int, success: int, failed: int) -> None:
    logger.info(
        "BATCH total=%d success=%d failed=%d",
        total,
        success,
        failed,
    )


def read_failed_accessions(log_path: Path) -> list[tuple[str, str]]:
    if not log_path.exists():
        raise FileNotFoundError(f"Arquivo de log não encontrado: {log_path}")

    latest_state: dict[str, tuple[bool, str]] = {}
    pattern = re.compile(
        r"(?P<status>SUCCESS|FAIL) accession=(?P<accession>\S+) backend=(?P<backend>\S+)"
    )

    for line in log_path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if not match:
            continue

        status = match.group("status")
        accession = match.group("accession")
        backend = match.group("backend")
        latest_state[accession] = (status == "SUCCESS", backend)

    return [
        (accession, backend)
        for accession, (is_success, backend) in latest_state.items()
        if not is_success
    ]
