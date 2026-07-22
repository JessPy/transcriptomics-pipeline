from pathlib import Path

from transcriptomics_pipeline.logger import (
    configure_file_logger,
    log_batch_summary,
    log_sample_failure,
    log_sample_success,
)


def test_log_sample_success(tmp_path: Path):
    sample_path = tmp_path / "sample.fastq.gz"
    sample_path.write_text("data", encoding="utf-8")
    log_path = tmp_path / "sample_log.txt"
    logger = configure_file_logger(log_path)

    log_sample_success(logger, "SRR000001", [sample_path], backend="ena")
    for handler in logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "SUCCESS accession=SRR000001 backend=ena" in content
    assert "sample.fastq.gz" in content
    assert "KiB" in content or "bytes" in content


def test_log_sample_failure(tmp_path: Path):
    log_path = tmp_path / "sample_log.txt"
    logger = configure_file_logger(log_path)

    log_sample_failure(logger, "SRR000002", "fastq-dump", RuntimeError("erro"))
    for handler in logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "FAIL accession=SRR000002 backend=fastq-dump" in content
    assert "erro" in content


def test_log_batch_summary(tmp_path: Path):
    log_path = tmp_path / "sample_log.txt"
    logger = configure_file_logger(log_path)

    log_batch_summary(logger, total=3, success=2, failed=1)
    for handler in logger.handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "BATCH total=3 success=2 failed=1" in content
