from pathlib import Path

import pytest

from transcriptomics_pipeline.readers import read_sample_accessions


def test_read_sample_accessions_from_csv(tmp_path: Path):
    sample = tmp_path / "samples.csv"
    sample.write_text("Sample Accession,Description\nSRR000001,Test\nSRR000002,Test 2\n", encoding="utf-8")

    accessions = read_sample_accessions(sample)

    assert accessions == ["SRR000001", "SRR000002"]


def test_read_sample_accessions_from_tsv_with_custom_column(tmp_path: Path):
    sample = tmp_path / "table.tsv"
    sample.write_text("accession\tgroup\nSRR000003\tA\nSRR000004\tB\n", encoding="utf-8")

    accessions = read_sample_accessions(sample, accession_column="accession")

    assert accessions == ["SRR000003", "SRR000004"]


def test_read_sample_accessions_from_plain_list(tmp_path: Path):
    sample = tmp_path / "list.txt"
    sample.write_text("SRR000005\nSRR000006\n", encoding="utf-8")

    accessions = read_sample_accessions(sample)

    assert accessions == ["SRR000005", "SRR000006"]


def test_read_sample_accessions_raises_when_column_missing(tmp_path: Path):
    sample = tmp_path / "samples.csv"
    sample.write_text("Name,Description\nSRR000007,Test\n", encoding="utf-8")

    with pytest.raises(ValueError):
        read_sample_accessions(sample)


def test_read_sample_accessions_from_excel(tmp_path: Path):
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Sample Accession", "Description"])
    sheet.append(["SRR000008", "Excel sample"])
    path = tmp_path / "samples.xlsx"
    workbook.save(path)

    accessions = read_sample_accessions(path)

    assert accessions == ["SRR000008"]
