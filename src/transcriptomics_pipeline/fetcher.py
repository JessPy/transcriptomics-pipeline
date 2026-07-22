from __future__ import annotations

import logging
import shutil
import subprocess
import zipfile
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .logger import log_sample_failure, log_sample_success

console = Console()
ENA_API_URL = "https://www.ebi.ac.uk/ena/portal/api/filereport"
FASTQ_DUMP_PROGRAMS = ("fasterq-dump", "fastq-dump")


def has_fastq_dump() -> bool:
    return any(shutil.which(program) for program in FASTQ_DUMP_PROGRAMS)


def _find_fastq_dump_program() -> str | None:
    for program in FASTQ_DUMP_PROGRAMS:
        path = shutil.which(program)
        if path:
            return path
    return None


def fetch_fastq_urls(accession: str) -> list[str]:
    params = {
        "accession": accession,
        "result": "read_run",
        "fields": "fastq_ftp",
        "format": "json",
    }
    response = httpx.get(ENA_API_URL, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    if not data or not isinstance(data, list):
        raise ValueError(f"Resposta inesperada da ENA para {accession}.")

    record = data[0]
    raw_ftp = record.get("fastq_ftp", "")
    if not raw_ftp:
        raise ValueError(f"Nenhum FASTQ disponível na ENA para {accession}.")

    raw_urls = [url.strip() for url in raw_ftp.split(";") if url.strip()]
    urls = [
        url if url.startswith(("http://", "https://")) else f"https://{url.lstrip('/')}"
        for url in raw_urls
    ]
    return urls


def fetch_run_accessions_for_bioproject(bioproject_accession: str) -> list[str]:
    params = {
        "accession": bioproject_accession,
        "result": "read_run",
        "fields": "run_accession",
        "format": "json",
    }
    response = httpx.get(ENA_API_URL, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    if not data or not isinstance(data, list):
        raise ValueError(f"Nenhum run encontrado para o BioProject {bioproject_accession}.")

    run_accessions = [
        str(item.get("run_accession", "")).strip()
        for item in data
        if str(item.get("run_accession", "")).strip()
    ]
    if not run_accessions:
        raise ValueError(f"Nenhum run encontrado para o BioProject {bioproject_accession}.")
    return run_accessions


def download_file(url: str, dest_dir: Path, progress: Progress) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_name = url.split("/")[-1]
    dest_path = dest_dir / file_name

    with httpx.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        total_bytes = int(response.headers.get("Content-Length", 0) or 0)

        task_id = progress.add_task(
            f"[cyan]Baixando {file_name}...", total=total_bytes
        )

        with open(dest_path, "wb") as handle:
            for chunk in response.iter_bytes(chunk_size=8192):
                handle.write(chunk)
                progress.update(task_id, advance=len(chunk))

    return dest_path


def _zip_files(files: list[Path], archive_path: Path) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=file_path.name)

    for file_path in files:
        file_path.unlink()

    return archive_path


def _download_from_ena(
    accession: str,
    outdir: Path,
    zip_output: bool = True,
    logger: logging.Logger | None = None,
) -> list[Path]:
    urls = fetch_fastq_urls(accession)
    if not urls:
        raise ValueError(f"Nenhum URL disponível para {accession}.")

    files: list[Path] = []
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        for url in urls:
            files.append(download_file(url, outdir, progress))

    if zip_output:
        archive_path = outdir / f"{accession}.zip"
        zipped = _zip_files(files, archive_path)
        if logger:
            log_sample_success(logger, accession, [zipped], backend="ena")
        return [zipped]

    if logger:
        log_sample_success(logger, accession, files, backend="ena")
    return files


def _download_with_fastq_dump(
    accession: str,
    outdir: Path,
    zip_output: bool = True,
    logger: logging.Logger | None = None,
) -> list[Path]:
    program = _find_fastq_dump_program()
    if program is None:
        raise RuntimeError(
            "Nenhum fastq-dump ou fasterq-dump disponível no PATH."
        )

    outdir.mkdir(parents=True, exist_ok=True)
    command = [program, accession, "-O", str(outdir), "--gzip", "--split-files"]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"fastq-dump falhou para {accession}: {result.stderr.strip() or result.stdout.strip()}"
        )

    files = sorted(outdir.glob(f"{accession}*.fastq*"))
    if not files:
        raise RuntimeError(
            f"fastq-dump não produziu arquivos de saída para {accession}."
        )

    if zip_output:
        archive_path = outdir / f"{accession}.zip"
        zipped = _zip_files(files, archive_path)
        if logger:
            log_sample_success(logger, accession, [zipped], backend="fastq-dump")
        return [zipped]

    if logger:
        log_sample_success(logger, accession, files, backend="fastq-dump")
    return files


def download_accession(
    accession: str,
    outdir: Path,
    backend: str = "ena",
    zip_output: bool = True,
    logger: logging.Logger | None = None,
) -> list[Path]:
    try:
        if backend.lower() == "ena":
            return _download_from_ena(
                accession,
                outdir,
                zip_output=zip_output,
                logger=logger,
            )

        if backend.lower() == "fastq-dump":
            return _download_with_fastq_dump(
                accession,
                outdir,
                zip_output=zip_output,
                logger=logger,
            )

        raise ValueError("backend deve ser 'ena' ou 'fastq-dump'.")
    except Exception as error:
        if logger:
            log_sample_failure(logger, accession, backend, error)
        raise
