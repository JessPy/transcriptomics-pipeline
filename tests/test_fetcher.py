import zipfile
from pathlib import Path

import httpx
import pytest

from transcriptomics_pipeline.fetcher import _zip_files, fetch_fastq_urls


def test_fetch_fastq_urls_parses_ftp_links(monkeypatch):
    response = httpx.Response(
        200,
        json=[
            {
                "fastq_ftp": "ftp.ebi.ac.uk/vol1/fastq/SRR000/SRR000001/SRR000001_1.fastq.gz;ftp.ebi.ac.uk/vol1/fastq/SRR000/SRR000001/SRR000001_2.fastq.gz"
            }
        ],
        request=httpx.Request("GET", "https://www.ebi.ac.uk"),
    )

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    urls = fetch_fastq_urls("SRR000001")

    assert urls == [
        "https://ftp.ebi.ac.uk/vol1/fastq/SRR000/SRR000001/SRR000001_1.fastq.gz",
        "https://ftp.ebi.ac.uk/vol1/fastq/SRR000/SRR000001/SRR000001_2.fastq.gz",
    ]


def test_fetch_fastq_urls_raises_when_no_fastq(monkeypatch):
    response = httpx.Response(
        200,
        json=[{"fastq_ftp": ""}],
        request=httpx.Request("GET", "https://www.ebi.ac.uk"),
    )
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    with pytest.raises(ValueError):
        fetch_fastq_urls("SRR000000")


def test_zip_files_creates_archive_and_removes_sources(tmp_path: Path):
    file_a = tmp_path / "sample_1.fastq.gz"
    file_b = tmp_path / "sample_2.fastq.gz"
    file_a.write_text("dummy1", encoding="utf-8")
    file_b.write_text("dummy2", encoding="utf-8")

    archive_path = tmp_path / "SRR000001.zip"
    zipped = _zip_files([file_a, file_b], archive_path)

    assert zipped == archive_path
    assert archive_path.exists()
    assert not file_a.exists()
    assert not file_b.exists()

    with zipfile.ZipFile(archive_path, "r") as archive:
        assert sorted(archive.namelist()) == ["sample_1.fastq.gz", "sample_2.fastq.gz"]
