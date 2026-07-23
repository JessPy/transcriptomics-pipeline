from pathlib import Path

import httpx
import pytest

from transcriptomics_pipeline.fetcher import _download_from_ena, fetch_fastq_urls


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


def test_download_from_ena_forces_gz(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "transcriptomics_pipeline.fetcher.fetch_fastq_urls",
        lambda accession: ["https://example.com/SRR000001_1.fastq"],
    )

    def fake_download_file(url, dest_dir, progress):
        path = dest_dir / "SRR000001_1.fastq"
        path.write_bytes(b"dummy")
        return path

    monkeypatch.setattr(
        "transcriptomics_pipeline.fetcher.download_file",
        fake_download_file,
    )

    files = _download_from_ena("SRR000001", tmp_path)

    assert len(files) == 1
    assert files[0].suffix == ".gz"
    assert files[0].name == "SRR000001_1.fastq.gz"
    assert files[0].exists()
