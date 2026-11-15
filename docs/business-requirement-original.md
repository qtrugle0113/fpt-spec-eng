# Original Business Requirement — Airflow Automation Tool

> **Provenance:** This is a business-level reconstruction of the initial product request from
> `specs/001-airflow-automation-tool/spec.md` and the user-facing product documentation. The
> original raw prompt submitted to `/speckit-specify` is not stored in this repository, so this
> document is not a verbatim quotation. It intentionally excludes later implementation decisions
> and detailed engineering constraints where possible.

## Business context

Data engineers need to move data between databases and delimited files on a recurring basis.
Preparing each workflow currently requires database setup, SQL, Python DAG development, and
operational knowledge of an orchestration platform. This makes routine ETL work slower and more
dependent on specialist developers.

## Product objective

Build a local tool that lets one data engineer or technically capable operator define, deploy,
run, and monitor routine ETL workflows through a web interface and Excel templates, without
writing Airflow DAG code or SQL DDL for the supported use cases.

The tool should use Apache Airflow to schedule and execute workflows and should provide sample
data so an operator can start the environment and try an end-to-end workflow.

## Users

- A data engineer who understands databases and needs to configure and operate ETL workflows.
- A local operator who starts the application and reviews workflow execution results.

The MVP is for one trusted local operator. It does not require application login or multi-user
access control.

## Business requirements

1. **Start and retain the environment.** The operator can start the complete application and its
   required services with a documented command. The system initializes itself, reports whether it
   is ready, includes sample data, and retains user data and workflow artifacts across restarts.
2. **Manage database connections.** The user can create, view, update, delete, and test reusable
   PostgreSQL and MySQL connections. Connection failures should be understandable, and stored
   credentials must not be exposed in ordinary views or results.
3. **Define destination tables.** The user can download an Excel template, describe one or more
   PostgreSQL or MySQL tables, review the proposed table creation, and explicitly confirm it.
   Validation errors should identify where the workbook needs correction. Existing user tables
   must not be silently replaced or changed.
4. **Prepare file sources.** The user can upload CSV or delimited TXT files, inspect a preview,
   validate the file, and use its stable reference in a workflow definition.
5. **Define ETL workflows in Excel.** The user can describe one or more workflows in an Excel
   template, including the source, destination, column mapping, schedule, retry behavior, and
   data-loading choice. The user can review the definition before deployment.
6. **Support the required data routes.** Workflows can move data between PostgreSQL and MySQL,
   including same-database and cross-database transfers, and from CSV/TXT files to either
   PostgreSQL or MySQL. The supported scope is eight source/target combinations.
7. **Map and load data predictably.** Users can explicitly map columns with different names or
   use compatible columns with matching names. Supported load choices are append, insert/update
   by a real key, and full replacement of the target data when separately authorized. The system
   should report processed rows and failures accurately.
8. **Handle large and failed runs safely.** Data transfer should work in batches without requiring
   the complete dataset to fit in worker memory. Failed, interrupted, or retried runs must not
   silently duplicate data, claim success for partial data, or replace a target with incomplete
   data. Operators should be able to understand run status and recovery needs.
9. **Deploy and operate workflows through Airflow.** The user can deploy a validated workflow,
   see whether Airflow accepted the right version, and activate a newly deployed workflow
   separately. New workflows should not begin scheduled execution without an explicit activation.
10. **Monitor execution.** The user can see workflows and their run history, status, timing,
    processed-row information, task details, and logs, and can open the corresponding workflow
    in Airflow. Unavailable information should be identified instead of fabricated.
11. **Configure workspace defaults.** The user can set and retain appropriate defaults for the
    local workspace.
12. **Provide a usable guide.** The application should include a Vietnamese user guide that can
    be read offline and printed or saved as PDF.

## Success measures

- Start a fresh environment with one documented command and run a sample workflow without
  manually configuring internal services.
- Create a destination table and deploy a first workflow within ten minutes of operator effort
  when the required sample workbook and connections are ready, without writing Python or SQL.
- Verify all eight supported source/target routes using real records, with correct values, keys,
  NULL handling, and row counts.
- Reject invalid workbooks with actionable location-specific errors and without unintended
  changes to data or workflows.
- Demonstrate correct repeated-run behavior for append, insert/update, and full replacement.
- Complete a dataset larger than twice the worker memory limit using at least twenty batches,
  with bounded resource use and evidence of temporary disk-based processing.
- Show accurate workflow and execution status, with run details traceable to actual orchestration
  results.

## Scope boundaries

Included: PostgreSQL, MySQL, CSV, delimited TXT, Excel-based table/workflow definitions, Airflow
scheduling and execution, local operation, monitoring, and sample data.

Excluded from the MVP: other database products, real-time streaming or CDC, distributed ETL,
arbitrary Python or SQL transformations, multi-source joins, Excel as an ETL data source,
multi-user authentication/authorization, automatic alteration or replacement of existing table
schemas, and overwriting workflows not managed by this application.

## Assumptions

- The operator has a supported container runtime and Compose provider installed and running.
- The operator can reach the required databases and has suitable database credentials/permissions.
- The default installation is for local use by one trusted operator, not a public or shared
  production service.
- Workflow templates and uploaded data files follow the formats documented by the application.

## Source mapping

The detailed source material is the product objective, user stories, requirements, business rules,
success criteria, assumptions, and out-of-scope section in
[`specs/001-airflow-automation-tool/spec.md`](../specs/001-airflow-automation-tool/spec.md).
