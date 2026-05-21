# Stack: Python

## Stack id

`python`

## Manifest fingerprints

- File globs: `**/pyproject.toml`, `**/requirements.txt`, `**/requirements-*.txt`, `**/setup.py`, `**/setup.cfg`, `**/Pipfile`, `**/*.py`
- Content patterns: `[tool.poetry]` / `[project]` table in `pyproject.toml`; `from setuptools import setup` in `setup.py`.
- Negative match: a `dags/` directory at the root with `airflow` in deps → dispatched to `data-platform.md` instead, even though Python tooling applies.

## Analysis-unit granularity

- **Monorepo with src-layout per package**: each `pyproject.toml` is one unit.
- **Poetry workspace** (workspaces support via plugins): each member is one unit.
- **Bazel `py_binary`**: each target is one unit.
- **Single-package repo**: the repo root is one unit.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-python`.
- Max AST depth: 5.
- Stdlib `ast` is the canonical fallback when tree-sitter is unavailable.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Flask | `http-route` | `@app.route('<path>', methods=[...])` / `@blueprint.route(...)` |
| FastAPI | `http-route` | `@app.get/post/...('<path>')` / `APIRouter.<verb>(...)` |
| Django views | `http-route` | function-based or class-based views registered in `urls.py` `urlpatterns` |
| Django REST Framework | `http-route` | `APIView` / `ViewSet` subclasses + `router.register(...)` |
| Starlette | `http-route` | `Route('<path>', endpoint, methods=[...])` |
| AWS Lambda handler | `http-route` if `APIGatewayProxyEvent`-shaped; `message-consumer` for SQS/SNS/Kinesis records; `scheduled-job` for `aws.events` event source | function with signature `def handler(event, context)` referenced in IaC |
| Celery task | `message-consumer` | `@app.task` decorator (Celery) |
| RQ worker | `message-consumer` | `@job(queue)` (rq) |
| APScheduler job | `scheduled-job` | `scheduler.add_job(fn, 'cron', ...)` |
| Click / Typer CLI | `cli-command` | `@click.command` / `@app.command` |
| Streamlit page | `ui-screen` | `streamlit.set_page_config` + page module under `pages/` |
| gRPC servicer | `grpc-method` | class inheriting `<Service>Servicer` from generated stub |
| GraphQL resolver | `graphql-resolver` | Strawberry `@strawberry.field`; Ariadne `QueryType().set_field` |
| SQLAlchemy event listener | `db-trigger` | `@event.listens_for(Model, '<event>')` |

## Inputs typing

- FastAPI: pydantic models in path/body/query parameters are first-class; the model schema is the source of truth.
- Flask: no built-in typing — `request.json`, `request.args`, `request.form` are treated as `dict[str, unknown]`. Marshmallow / pydantic schemas in the function body are detected as `inputs[].validation`.
- Django: `serializers.Serializer` subclasses provide typing for DRF endpoints.
- Function-level type hints (`def handler(event: APIGatewayProxyEvent, ...)`) are honored.

## Side-effect detection

- Persistence: SQLAlchemy `session.add/commit`, Django ORM `.save()` / `.create()` / `.update()`, Peewee, Tortoise ORM, raw `cursor.execute` with non-SELECT verbs.
- HTTP clients: `requests`, `httpx`, `urllib.request`, `aiohttp.ClientSession`.
- Message publishers: `boto3` `client('sqs').send_message`, `client('sns').publish`, `client('eventbridge').put_events`; `kafka-python` / `confluent-kafka` producers; `pika` (RabbitMQ).
- Filesystem and object storage: `open(..., 'w')`, `boto3` `client('s3').put_object`, `smart_open.open(..., 'w')`.
- Logging that includes user input → flagged as potential `error-message leakage` candidate.

## Cross-stack bridge hints

- `requests.get("http://...")` / `httpx.AsyncClient().post(url)` → `http-route` resolution across units.
- `boto3.client('lambda').invoke(FunctionName='<name>')` → `aws-serverless` lookup by lambda name.
- `pydantic` shared schema package imported across units → record the schema as a boundary contract.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column `python` =
`MUST-if-applicable`. Specifically: mutable default arguments leading to
state leakage, datetime naive vs aware (TZ bugs), `Decimal` vs `float`
money rounding, async/await missing `await` (coroutine never executed),
N+1 in Django ORM, retry without idempotency token, SQLAlchemy session
leakage across requests, Lambda cold-start global state mutation.

## Empty-input branch

If a unit is detected as `python` but **zero** entry points are extracted
(e.g. a pure utility library), the unit is recorded in `coverage.md` with
skip reason `no-entry-points`. Notebooks (`*.ipynb`) are excluded by
default unless `args.skip_paths` is overridden to include them; reason
recorded is `out-of-scope`.
