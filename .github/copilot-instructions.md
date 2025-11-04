# dbt-fabricspark-plainsight Development Guide

## Project Context

This is a **Plainsight-maintained fork** of microsoft/dbt-fabricspark, created due to insufficient maintenance of the upstream project. This is a dbt adapter that enables dbt to work with Microsoft Fabric Spark (Synapse Spark) via Livy API sessions over HTTP.

## Architecture Overview

### Core Components

1. **Connection Layer** (`src/dbt/adapters/fabricspark/connections.py`)
   - `FabricSparkConnectionManager`: Manages thread-local connection lifecycle
   - Connection method: `LIVY` only (no direct ODBC/Thrift support for Fabric)
   - Retry logic: Built-in with configurable `connect_retries` and `retry_all` flag
   - Global connection pool per thread stored in `connection_managers` dict

2. **Livy Session Management** (`src/dbt/adapters/fabricspark/livysession.py`)
   - `LivySessionManager`: Singleton pattern managing a global Livy session
   - **Critical**: Single session reused across all queries in a thread to avoid overhead
   - Session creation takes minutes - always check `is_valid_session()` before recreating
   - Authentication: Azure CLI (`az login`) or Service Principal credentials
   - Token refresh: Auto-refreshes when <5 minutes until expiry

3. **Adapter Implementation** (`src/dbt/adapters/fabricspark/impl.py`)
   - `FabricSparkAdapter`: Extends SQLAdapter with Spark-specific SQL generation
   - Uses Jinja macros in `src/dbt/include/fabricspark/macros/` for SQL templating
   - Constraint support: All constraints are `NOT_ENFORCED` (Spark limitation)
   - Catalog operations use `DESCRIBE EXTENDED` and `SHOW TABLES` (handles v2 Iceberg tables)

4. **Shortcuts Feature** (`src/dbt/adapters/fabricspark/shortcuts.py`)
   - Creates Fabric shortcuts to external data sources via REST API
   - Configured via `shortcuts_json_str` in profile or `shortcuts.json` file
   - Auto-deletes and recreates if source path/workspace/item ID mismatch detected

### Authentication Flow

```python
# Priority order for token acquisition:
if credentials.authentication == "cli":
    # Uses AzureCliCredential - requires `az login`
elif credentials.authentication == "int_tests":
    # Uses provided accessToken directly
else:
    # Uses ClientSecretCredential with tenant_id/client_id/client_secret
```

### SQL Execution Pattern

1. Get thread connection from pool
2. Check if Livy session exists and is valid
3. If invalid/missing: create new session (slow!)
4. Submit SQL via POST to `/sessions/{id}/statements`
5. Poll `/statements/{statement_id}` until `state == "available"`
6. Parse response JSON for data/schema or error

## Development Workflows

### Installation

Users can install this fork directly from GitHub:

```bash
# Install latest from main branch
pip install git+https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git

# Install specific version/tag
pip install git+https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git@v1.9.0

# Install specific branch
pip install git+https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git@feature-branch
```

### Environment Setup

```bash
# Clone repository
git clone https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git
cd dbt-fabricspark-plainsight

# Install with uv (preferred package manager for development)
uv pip install -e . --group dev

# After installing packages with uv, sync lock file
uv sync
```

### Running Tests

```bash
# Setup test credentials
cp test.env.example test.env
# Edit test.env with your Fabric workspace/lakehouse IDs

# Run unit tests
uv run pytest tests/unit/

# Run functional tests (requires valid Fabric connection)
uv run pytest --profile az_cli tests/functional/

# Run specific test suites
uv run pytest tests/functional/adapter/basic/
```

**Test credentials required** in `test.env`:
- `DBT_FABRIC_SPARK_WORKSPACE_ID`: Fabric workspace GUID
- `DBT_FABRIC_SPARK_LAKEHOUSE_ID`: Lakehouse GUID  
- `DBT_FABRIC_SPARK_LAKEHOUSE_NAME`: Lakehouse name
- Service principal creds OR use `authentication: CLI` with `az login`

### Linting and Formatting

```bash
# Uses ruff (configured in pyproject.toml)
ruff check .
ruff format .
```

Line length: 99 characters, quote style: double

### Profile Configuration

Example `profiles.yml` for local development:

```yaml
fabricspark-dev:
  target: dev
  outputs:
    dev:
      type: fabricspark
      method: livy
      authentication: CLI  # or use SPN with client_id/client_secret/tenant_id
      endpoint: https://api.fabric.microsoft.com/v1
      workspaceid: <workspace-guid>
      lakehouseid: <lakehouse-guid>
      lakehouse: <lakehouse-name>
      schema: <schema-name>
      threads: 1
      connect_retries: 3
      connect_timeout: 10
      retry_all: true
      spark_config:
        name: "dbt-session"  # Required!
```

**Critical config notes:**
- `spark_config.name` is **required** (will raise ValueError if missing)
- `database` field not supported - raises error if set (use `lakehouse` instead)
- `retry_all: true` retries all connection errors, not just known retryable ones

## Project-Specific Patterns

### Macro Dispatching

Macros use `adapter.dispatch()` pattern to override dbt-core defaults:

```sql
{% macro create_temporary_view(relation, compiled_code) -%}
  {{ return(adapter.dispatch('create_temporary_view', 'dbt')(relation, compiled_code)) }}
{%- endmacro -%}

{% macro fabricspark__create_temporary_view(relation, compiled_code) -%}
  create or replace temporary view {{ relation }} as
    {{ compiled_code }}
{%- endmacro -%}
```

Prefix with `fabricspark__` for adapter-specific implementations.

### Incremental Strategies

Supported strategies (validated in `incremental.sql` macro):
- `append`: Simple INSERT
- `insert_overwrite`: Partition overwrite (requires `partition_by`)
- `merge`: Delta Lake MERGE (requires `file_format: delta` and `unique_key`)
- `microbatch`: Time-based incremental processing

**Delta format is default** (`file_format: delta`) and required for merge strategy.

### Error Handling

Retryable error detection via keyword matching in `_is_retryable_error()`:
```python
retryable_keywords = [
    "pending", "temporary", "retry", "timeout", "unavailable",
    "transient", "throttling", "rate limit", "connection reset", "service busy"
]
```

Common error messages checked:
- `[TABLE_OR_VIEW_NOT_FOUND]`, `NoSuchTableException`: Normalized to empty result
- `Database 'X' not found`: Returns empty list instead of error
- `SHOW TABLE EXTENDED is not supported for v2 tables`: Falls back to `SHOW TABLES` + `DESCRIBE`

### Version Management

Version defined in `src/dbt/adapters/fabricspark/__version__.py`:
```python
version = "1.9.0"
```

Used by `hatchling` build backend via `tool.hatch.version.path` in `pyproject.toml`.

## Common Pitfalls

1. **Don't create multiple Livy sessions**: Session creation is slow (~minutes). Always reuse via `LivySessionManager.livy_global_session`.

2. **Strip trailing semicolons**: Livy SQL executor fails with trailing `;` - handled in `LivySessionConnectionWrapper.execute()`.

3. **No transaction support**: `begin()`, `commit()`, `rollback()` are no-ops. Don't rely on transactional semantics.

4. **Backtick quoting**: Use backticks for identifiers: `` `schema`.`table` `` (implemented in `quote()` method).

5. **Spark version detection**: Adapter queries Spark version on first connection and sets `DBT_SPARK_VERSION` env var for conditional SQL logic.

## Testing Against Upstream

When contributing fixes that should go upstream:

1. Test against this fork first
2. Submit PR to this repo
3. Consider submitting to [microsoft/dbt-fabricspark](https://github.com/microsoft/dbt-fabricspark)
4. Note in PR description if already submitted upstream

## Key Files Reference

- **Entry point**: `src/dbt/adapters/fabricspark/__init__.py`
- **Profile template**: `src/dbt/include/fabricspark/profile_template.yml`
- **Macro library**: `src/dbt/include/fabricspark/macros/` (50+ SQL macros)
- **Test fixtures**: `tests/functional/` uses pytest with `dbt-tests-adapter` framework
