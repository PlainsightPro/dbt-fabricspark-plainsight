# dbt-fabricspark-plainsight

> **⚠️ IMPORTANT: Custom Fork Notice**
> 
> This is a **custom fork** of [microsoft/dbt-fabricspark](https://github.com/microsoft/dbt-fabricspark) maintained by **Plainsight**. 
> 
> **Why this fork exists:**
> - The original repository is not sufficiently maintained
> - Pull requests are not being resolved in a timely manner
> 
> This fork is maintained specifically for dbt-fabricspark projects and includes fixes, improvements, and features that are critical for our work.

---

<a href="https://github.com/microsoft/dbt-fabricspark/actions/workflows/integration.yml">
  <img src="https://github.com/microsoft/dbt-fabricspark/actions/workflows/integration.yml/badge.svg?branch=main&event=pull_request" alt="Adapter Integration Tests"/>
</a>

<br>
[dbt](https://www.getdbt.com/) enables data analysts and engineers to transform their data using the same practices that software engineers use to build applications.

dbt is the T in ELT. Organize, cleanse, denormalize, filter, rename, and pre-aggregate the raw data in your warehouse so that it's ready for analysis.

## About dbt-fabricspark

The `dbt-fabricspark` package contains all of the code enabling dbt to work with Synapse Spark in Microsoft Fabric. For more information, consult [the docs](https://docs.getdbt.com/docs/profile-fabricspark).

### ✨ Features in This Fork

- **PySpark Model Support**: Write dbt models in Python/PySpark for advanced data transformations
- **dbt 1.9.2 Compatible**: Updated to work with the latest dbt-core and dbt-adapters APIs
- **FabricSparkRelationType**: Custom relation type class for better type safety and compatibility
- **Enhanced Stability**: Additional bug fixes and improvements not yet in upstream

## Installation

Install directly from GitHub using pip:

```bash
pip install git+https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git
```

Or install a specific version/tag:

```bash
# Install specific version/tag
pip install git+https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git@v1.9.2
```

For development installation:

```bash
git clone https://github.com/PlainsightPro/dbt-fabricspark-plainsight.git
cd dbt-fabricspark-plainsight
pip install -e .
```

## Getting started

- [Install dbt](https://docs.getdbt.com/docs/installation)
- Read the [introduction](https://docs.getdbt.com/docs/introduction/) and [viewpoint](https://docs.getdbt.com/docs/about/viewpoint/)

## Running locally

Use Livy endpoint to connect to Synapse Spark in Microsoft Fabric. Configure your profile to connect via Livy endpoints.

Create a profile like this one:

```yaml
fabric-spark-test:
  target: fabricspark-dev
  outputs:
    fabricspark-dev:
        authentication: CLI  # or use client_id/client_secret/tenant_id for SPN
        method: livy
        connect_retries: 3
        connect_timeout: 10
        endpoint: https://api.fabric.microsoft.com/v1
        workspaceid: <your-workspace-guid>
        lakehouseid: <your-lakehouse-guid>
        lakehouse: <your-lakehouse-name>
        schema: <your-schema>
        threads: 1
        type: fabricspark
        retry_all: true
        spark_config:
          name: "dbt-session"  # Required!
```

### PySpark Models

This fork supports Python models using PySpark! Create `.py` files in your `models/` directory:

```python
# models/my_pyspark_model.py
def model(dbt, session):
    """
    Parameters:
        dbt: dbt context with config, this, ref(), source() methods
        session: Active PySpark session
    
    Returns:
        PySpark DataFrame
    """
    # Load data using dbt's ref() or source()
    source_df = dbt.ref("source_model")
    
    # Apply PySpark transformations
    from pyspark.sql import functions as F
    
    result_df = source_df.filter(F.col("status") == "active") \
                         .groupBy("category") \
                         .agg(F.count("*").alias("count"))
    
    return result_df
```

Run it like any other dbt model:
```bash
dbt run --select my_pyspark_model
```

## Reporting bugs and contributing code

- Want to report a bug or request a feature? Open [an issue](https://github.com/PlainsightPro/dbt-fabricspark-plainsight/issues/new) in this repository
- Want to contribute? Check out the [Contributing Guide](https://github.com/PlainsightPro/dbt-fabricspark-plainsight/blob/HEAD/CONTRIBUTING.md)
- For the upstream project: Visit [microsoft/dbt-fabricspark](https://github.com/microsoft/dbt-fabricspark)

## Join the dbt Community

- Be part of the conversation in the [dbt Community Slack](http://community.getdbt.com/)
- Read more on the [dbt Community Discourse](https://discourse.getdbt.com)

## Code of Conduct

Everyone interacting in the dbt project's codebases, issue trackers, chat rooms, and mailing lists is expected to follow the [dbt Code of Conduct](https://community.getdbt.com/code-of-conduct).
