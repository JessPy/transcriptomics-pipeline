import httpx

from transcriptomics_pipeline.cli import resolve_bioproject, retry_failed_accessions
from transcriptomics_pipeline.fetcher import fetch_run_accessions_for_bioproject


def test_fetch_run_accessions_for_bioproject(monkeypatch):
    response = httpx.Response(
        200,
        json=[{"run_accession": "SRR000001"}, {"run_accession": "SRR000002"}],
        request=httpx.Request("GET", "https://www.ebi.ac.uk"),
    )
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)

    runs = fetch_run_accessions_for_bioproject("PRJNA123456")

    assert runs == ["SRR000001", "SRR000002"]


def test_resolve_bioproject_downloads_runs(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        "transcriptomics_pipeline.cli.fetch_run_accessions_for_bioproject",
        lambda accession: ["SRR000001", "SRR000002"],
    )

    def fake_download_accession(accession, outdir, backend="ena", logger=None):
        calls.append((accession, outdir, backend))
        return []

    monkeypatch.setattr(
        "transcriptomics_pipeline.cli.download_accession",
        fake_download_accession,
    )

    result = resolve_bioproject(
        "PRJNA123456",
        outdir=tmp_path,
        download=True,
        backend="ena",
    )

    assert result is None
    assert (tmp_path / "PRJNA123456_runs.txt").exists()
    assert calls == [
        ("SRR000001", tmp_path / "SRR000001", "ena"),
        ("SRR000002", tmp_path / "SRR000002", "ena"),
    ]


def test_retry_failed_accessions_uses_only_failures(monkeypatch, tmp_path):
    log_path = tmp_path / "sample_log.txt"
    log_path.write_text(
        "INFO START accession=SRR000001 backend=ena zip_output=False\n"
        "ERROR FAIL accession=SRR000001 backend=ena error=boom\n"
        "INFO SUCCESS accession=SRR000002 backend=ena path=/tmp/SRR000002.fastq size=10 bytes\n"
        "ERROR FAIL accession=SRR000003 backend=ena error=boom\n",
        encoding="utf-8",
    )

    calls = []

    def fake_download_accession(accession, outdir, backend="ena", logger=None):
        calls.append((accession, outdir, backend))
        return []

    monkeypatch.setattr(
        "transcriptomics_pipeline.cli.download_accession",
        fake_download_accession,
    )

    retry_failed_accessions(
        outdir=tmp_path,
        backend="fastq-dump",
        log_path=log_path,
    )

    assert calls == [
        ("SRR000001", tmp_path / "SRR000001", "fastq-dump"),
        ("SRR000003", tmp_path / "SRR000003", "fastq-dump"),
    ]
