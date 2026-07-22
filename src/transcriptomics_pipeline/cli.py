from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .fetcher import (
    download_accession,
    fetch_run_accessions_for_bioproject,
    has_fastq_dump,
)
from .logger import configure_file_logger, log_batch_summary
from .readers import read_sample_accessions
from .utils import ensure_directory

app = typer.Typer(
    help="Ferramenta para baixar FASTQs de ENA/SRA a partir de tabelas flexíveis."
)
console = Console()

DEFAULT_OUTDIR = Path("./data/raw")
DEFAULT_ACCESSION_COLUMN = "Sample Accession"
DEFAULT_LOG_FILENAME = "sample_log.txt"
ACCESSION_ARG = typer.Argument(
    ...,
    help="ID de acesso da amostra (Ex: SRR12345678, ERR1039508 ou PRJNA...).",
)
TABLE_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=False,
    readable=True,
    help="Caminho para o arquivo de amostras (CSV, TSV, TXT ou XLSX).",
)
OUTDIR_OPTION = typer.Option(
    DEFAULT_OUTDIR,
    "--outdir",
    "-o",
    help="Diretório onde os arquivos serão salvos.",
)
RESOLVE_OUTDIR_OPTION = typer.Option(
    DEFAULT_OUTDIR,
    "--outdir",
    "-o",
    help="Diretório onde a lista de SRR será salva.",
)
BACKEND_OPTION = typer.Option(
    "ena",
    "--backend",
    "-b",
    case_sensitive=False,
    show_choices=True,
    help="Fonte de download: ena ou fastq-dump.",
)
ACCESSION_COLUMN_OPTION = typer.Option(
    DEFAULT_ACCESSION_COLUMN,
    "--accession-column",
    "-c",
    help="Nome da coluna que contém as accessions no arquivo.",
)
ZIP_OUTPUT_OPTION = typer.Option(
    True,
    "--zip-output/--no-zip-output",
    help="Compacta os resultados em um .zip e remove os arquivos intermediários.",
)
DOWNLOAD_OPTION = typer.Option(
    False,
    "--download/--no-download",
    help="Baixa automaticamente cada SRR encontrada após listar o BioProject.",
)


@app.command()
def download(
    accession: str = ACCESSION_ARG,
    outdir: Path = OUTDIR_OPTION,
    backend: str = BACKEND_OPTION,
    zip_output: bool = ZIP_OUTPUT_OPTION,
):
    """Baixa FASTQ para uma accession única usando ENA ou fastq-dump."""
    outdir = ensure_directory(outdir)
    logger = configure_file_logger(outdir / DEFAULT_LOG_FILENAME)
    logger.info(
        "START accession=%s backend=%s zip_output=%s",
        accession,
        backend,
        zip_output,
    )

    try:
        download_accession(
            accession,
            outdir,
            backend=backend,
            zip_output=zip_output,
            logger=logger,
        )
        archive_message = "arquivo zip" if zip_output else "arquivos brutos"
        console.print(
            f"[bold green]✔ Downloads concluídos para {accession}." \
            f" {archive_message.capitalize()} salvos em [underline]{outdir.resolve()}[/underline]."
        )
    except Exception as error:
        console.print(f"[bold red]Erro:[/bold red] {error}")
        raise typer.Exit(code=1) from None


@app.command("resolve-bioproject")
def resolve_bioproject(
    bioproject: str = typer.Argument(
        ...,
        help="Accession do BioProject (por exemplo, PRJNA123456).",
    ),
    outdir: Path = RESOLVE_OUTDIR_OPTION,
    download: bool = DOWNLOAD_OPTION,
    backend: str = BACKEND_OPTION,
    zip_output: bool = ZIP_OUTPUT_OPTION,
):
    """Resolve um BioProject em uma lista de SRRs via API da ENA."""
    outdir = ensure_directory(outdir)
    try:
        run_accessions = fetch_run_accessions_for_bioproject(bioproject)
    except Exception as error:
        console.print(f"[bold red]Erro:[/bold red] {error}")
        raise typer.Exit(code=1) from None

    output_path = outdir / f"{bioproject}_runs.txt"
    output_path.write_text("\n".join(run_accessions) + "\n", encoding="utf-8")
    console.print(
        f"[bold green]✔ {len(run_accessions)} SRR(s) encontrados para {bioproject}.[/bold green]"
    )
    console.print(f"📄 Lista salva em: [underline]{output_path.resolve()}[/underline]")

    if not download:
        return

    success_count = 0
    for accession in run_accessions:
        sample_dir = ensure_directory(outdir / accession)
        console.print(f"[bold blue]🔽 Baixando {accession}...[/bold blue]")
        try:
            download_accession(
                accession,
                sample_dir,
                backend=backend,
                zip_output=zip_output,
            )
            success_count += 1
        except Exception as error:
            console.print(f"[bold red]Falha para {accession}:[/bold red] {error}")

    console.print(
        f"[bold green]✔ Downloads concluídos: {success_count}/{len(run_accessions)} SRR(s).[/bold green]"
    )


@app.command("batch")
def batch(
    table: Path = TABLE_ARGUMENT,
    accession_column: str = ACCESSION_COLUMN_OPTION,
    outdir: Path = OUTDIR_OPTION,
    backend: str = BACKEND_OPTION,
    zip_output: bool = ZIP_OUTPUT_OPTION,
):
    """Lê uma tabela de amostras e baixa FASTQs para todas as accessions presentes."""
    outdir = ensure_directory(outdir)
    logger = configure_file_logger(outdir / DEFAULT_LOG_FILENAME)
    logger.info(
        "START batch table=%s backend=%s zip_output=%s",
        table.name,
        backend,
        zip_output,
    )

    try:
        accessions = read_sample_accessions(table, accession_column)
    except Exception as error:
        console.print(f"[bold red]Erro ao ler a tabela:[/bold red] {error}")
        raise typer.Exit(code=1) from None

    console.print(
        f"[bold blue]🔍 Encontradas {len(accessions)} accessions em {table.name}.[/bold blue]"
    )

    if backend.lower() == "fastq-dump" and not has_fastq_dump():
        console.print(
            "[bold yellow]Aviso:[/bold yellow] fastq-dump ou fasterq-dump não está instalado."
        )
        raise typer.Exit(code=1)

    success_count = 0
    for accession in accessions:
        sample_dir = ensure_directory(outdir / accession)
        console.print(f"[bold blue]🔽 Baixando {accession}...[/bold blue]")

        try:
            download_accession(
                accession,
                sample_dir,
                backend=backend,
                zip_output=zip_output,
                logger=logger,
            )
            success_count += 1
        except Exception as error:
            console.print(f"[bold red]Falha para {accession}:[/bold red] {error}")

    failed_count = len(accessions) - success_count
    log_batch_summary(logger, len(accessions), success_count, failed_count)
    console.print(
        f"\n[bold green]✔ Batch concluído: {success_count}/{len(accessions)} accessions baixadas com sucesso.[/bold green]"
    )


if __name__ == "__main__":
    app()
