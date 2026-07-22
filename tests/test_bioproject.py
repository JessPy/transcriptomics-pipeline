import httpx

from transcriptomics_pipeline.cli import resolve_bioproject
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

    def fake_download_accession(accession, outdir, backend="ena", zip_output=True, logger=None):
        calls.append((accession, outdir, backend, zip_output))
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
        zip_output=False,
    )

    assert result is None
    assert (tmp_path / "PRJNA123456_runs.txt").exists()
    assert calls == [
        ("SRR000001", tmp_path / "SRR000001", "ena", False),
        ("SRR000002", tmp_path / "SRR000002", "ena", False),
    ]
