# Transcriptomics Pipeline

Pipeline Python profissional para baixar FASTQ de ENA/SRA usando tabelas flexíveis.

## Recursos

- Suporte a arquivos CSV, TSV, TXT e XLSX
- Identifica automaticamente colunas como `Sample Accession`, `accession`, `Run Accession` e variantes
- Download direto via API ENA ou via `fastq-dump/fasterq-dump`
- Estrutura de projeto pronta para Poetry e testes com pytest

## Instalação

```bash
poetry install
```

## Uso

Download de uma accession única via ENA:

```bash
poetry run transcriptomics-pipeline download-unico SRR12345678 -o data/raw
```

Download em lote com arquivo de amostras:

```bash
poetry run transcriptomics-pipeline download amostras.csv --accession-column "Sample Accession" -o data/raw
```

Usando `fastq-dump` como backend:

```bash
poetry run transcriptomics-pipeline download-unico SRR12345678 --backend fastq-dump -o data/raw
```

Os arquivos são salvos como `*.fastq.gz` (forçando gzip) e não são empacotados em `.zip`.

Logs de amostras são gerados em `data/raw/sample_log.txt` por padrão. O arquivo contém:

- accession
- backend usado
- caminho do arquivo resultante
- tamanho em formato legível
- falhas e mensagens de erro

## Resolver BioProject em SRR

```bash
poetry run transcriptomics-pipeline resolve-bioproject PRJNA123456 -o data/raw --download
```

Esse comando salva uma lista de runs em `data/raw/PRJNA123456_runs.txt` e, com `--download`, já inicia o download de cada SRR encontrado em uma pasta própria.

## Reprocessar apenas as falhas

Se alguma amostra falhar em uma execução anterior, você pode repetir apenas os itens marcados como falha no log:

```bash
poetry run transcriptomics-pipeline retry-failures -o data/raw --backend fastq-dump
```

Esse comando lê o arquivo de log padrão `data/raw/sample_log.txt`, identifica as accessions com falha e tenta baixar somente elas novamente. Se você quiser trocar o backend da tentativa, basta passar `--backend ena` ou `--backend fastq-dump`.

## Siglas do SRA

A documentação das siglas principais está em [docs/sra_abbreviations.md](docs/sra_abbreviations.md).

## Formatos de tabela suportados

- CSV
- TSV
- TXT com uma coluna de accessions
- XLSX

## Desenvolvimento

Executar testes:

```bash
poetry run pytest
```

Verificar estilo com Ruff:

```bash
poetry run ruff check src tests
```
