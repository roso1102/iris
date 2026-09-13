# Build-cache benchmark — 2026-09-13

## Change measured

Moved the Docling model warm-up layer before application source copies and
added an Artifact Registry `pull-cache` step plus Docker `--cache-from` to the
ingestion-worker and retrieval-api Cloud Build configurations.

## Results

| Image | Previous build | Cached build | Change |
|---|---:|---:|---:|
| ingestion-worker | 12m 25s (`8fa27c48`) | 6m 16s (`f30f179f`) | 49.5% faster |
| retrieval-api | 2m 18s (`ea6debc8`) | 1m 10s (`ec678a5f`) | 49.3% faster |

The cached ingestion build spent approximately 5m 25s pulling the existing
image and 20s executing the Docker build. The application/model layers were
reused successfully. This is the first cache-enabled run; later runs should
benefit further when the registry image is already warm in the builder.

## Deployment verification

- Workflow: `34770777304` — successful.
- Ingestion revision: `ingestion-worker-00009-8ns` — Ready, 100% traffic.
- Retrieval revision: `retrieval-api-00004-pvj` — Ready, 100% traffic.
- No runtime code or IAM changes were introduced.

## Follow-up

Use immutable SHA tags and a dedicated small cache image if concurrent builds
make the `latest` pull expensive or create cache races. Keep the current
`latest` cache as the staging baseline until that measurement is available.
