# Embedding Index Rebuild Workflow

## Overview

The rebuild workflow regenerates all `knowledge_chunks` embeddings using the configured embedding provider. It handles dimension changes (ALTER COLUMN with HNSW index drop/recreate), records build metadata, and enforces safety checks before modifying the database.

## CLI Usage

```bash
# Dry-run (default) — shows what would happen
uv run python scripts/rebuild_embeddings.py

# Rebuild with current EMBEDDING_* env vars
uv run python scripts/rebuild_embeddings.py --confirm

# Override provider/model/dimension
uv run python scripts/rebuild_embeddings.py --provider openai_compatible --dimension 1024 --confirm

# Allow changing vector column dimension (384 -> 1024)
uv run python scripts/rebuild_embeddings.py --provider openai_compatible --dimension 1024 --allow-dimension-reset --confirm
```

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--dry-run` | True | Show what would be done without writing |
| `--confirm` | False | Actually write to the database |
| `--allow-dimension-reset` | False | Allow changing vector column dimension (drops/recreates HNSW index) |
| `--provider` | EMBEDDING_PROVIDER env | Override provider name |
| `--model` | EMBEDDING_MODEL env | Override model name |
| `--dimension` | EMBEDDING_DIM env | Override vector dimension |
| `--batch-size` | EMBEDDING_BATCH_SIZE env | Override batch size |

Exit code: 0 on success/skip/dry-run, 1 on failure/blocked.

## Workflow Steps

### 1. Create Provider

The provider is created from the config (CLI overrides merged with env defaults). Provider creation validates API key presence for real providers. Failure at this step returns `status: "failed"`.

### 2. Read Current Metadata

Reads the latest record from `embedding_index_metadata`. If metadata exists, the config fingerprint is compared:

- **Fingerprint matches**: a note is logged that embeddings are up-to-date
- **Fingerprint differs**: the old and new configs are logged for audit
- **No metadata**: logged as a fresh build

### 3. Check DB Vector Dimension

Queries `pg_attribute` for the `embedding` column's type modifier (`atttypmod >> 16` gives the vector dimension). Also checks whether the HNSW index exists.

- **Dimension matches**: proceed
- **Dimension mismatch without `--allow-dimension-reset`**: fail with clear error
- **Dimension mismatch with `--allow-dimension-reset`**: the HNSW index will be dropped, the column altered, and the index recreated

### 4. Fetch Chunks

Fetches all chunk IDs and content from `knowledge_chunks` (sorted by doc_type, id). Also counts source documents from `knowledge_faq`, `knowledge_policy`, `knowledge_case`.

- **No chunks found**: return `status: "skipped"` immediately

### 5. Dry-run Check

If `--dry-run` is active (default), returns `status: "dry_run"` with a summary of steps. This is the default behavior — no changes are made without explicit opt-in.

### 6. Confirm Check

If `--confirm` is not set, returns `status: "blocked"` with instructions to pass `--confirm`. (When `--confirm` is absent, `--dry-run` is forced on regardless of explicit `--dry-run` flag.)

### 7. Execute Rebuild

#### 7a. Drop HNSW Index (if dimension changes)

If the DB dimension differs from the provider dimension, the existing `idx_chunks_embedding_hnsw` index is dropped to allow the column type change.

#### 7b. Alter Column Type (if dimension changes)

```sql
ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(new_dim)
```

#### 7c. Generate and Update Embeddings

All chunk content texts are collected and passed to `provider.embed_batch(texts)`. A count mismatch between inputs and outputs raises a RuntimeError. Each embedding is converted to PostgreSQL vector array string `[x,y,z]` format and updated via:

```sql
UPDATE knowledge_chunks SET embedding = %s::vector WHERE id = %s
```

All operations run in a single transaction.

#### 7d. Recreate HNSW Index (if it was dropped)

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON knowledge_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200)
```

#### 7e. Write Metadata

A new `EmbeddingIndexMetadata` record is inserted with provider name, model name, dimension, batch size, source record count, chunk count, embedding count, config fingerprint, and a note identifying the rebuild script.

## Return Statuses

| Status | Meaning |
|--------|---------|
| `completed` | Embeddings rebuilt successfully |
| `skipped` | No chunks found — nothing to rebuild |
| `dry_run` | Dry-run mode — no changes written |
| `blocked` | `--confirm` not provided |
| `failed` | Provider creation error, dimension mismatch without reset flag, or rebuild exception |

## Exit Codes

- 0: `completed`, `skipped`, or `dry_run`
- 1: `blocked` or `failed`

## Metadata Tracking

The `embedding_index_metadata` table stores one record per rebuild:

| Column | Description |
|--------|-------------|
| `provider_name` | e.g. "fake", "openai_compatible" |
| `model_name` | e.g. "sha-256", "text-embedding-v4" |
| `dimension` | Vector dimension |
| `batch_size` | Batch size used |
| `built_at` | Timestamp |
| `source_record_count` | Source documents processed |
| `chunk_count` | Number of chunks |
| `embedding_count` | Number of embeddings generated |
| `config_fingerprint` | SHA-256(provider\|model\|dimension)[:16] |
| `notes` | Build description |

## Source Code

- `scripts/rebuild_embeddings.py` — CLI and workflow logic
- `src/ticketpilot/retrieval/embedding_metadata.py` — metadata dataclass, DB read/write, dimension detection
- `db/migrations/004_add_embedding_metadata.sql` — metadata table migration

## Tests

- `tests/unit/test_rebuild_embeddings.py` — 10 tests covering dry-run, dimension handling, edge cases, and full rebuild flow (all mocked, no DB)
- `tests/unit/test_embedding_metadata.py` — 10 tests for the metadata dataclass (fingerprint, serialization, round-trip)
