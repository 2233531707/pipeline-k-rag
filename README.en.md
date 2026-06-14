# Underground Pipeline Knowledge Model Database (Pipeline-K-RAG)

A multi-user agent platform for underground pipeline, enterprise-document, and geospatial knowledge. It connects RAG, explicit knowledge-graph retrieval, portable knowledge bases, PostGIS analysis, layer composition, and interactive chat maps to one LangGraph runtime.

[中文](README.md) · [Architecture](ARCHITECTURE.md) · [Documentation](docs/intro/project-overview.md) · [MIT License](LICENSE)

## Highlights

- Configurable agents with built-in tools, knowledge tools, MCP, Skills, and SubAgents.
- Milvus document/entity/triple vectors with Neo4j relationships.
- Explicit `query_knowledge_graph` and graph-seeded `query_kb(graph_entity_ids=...)`.
- Independent Chat model, schema, concurrency, and parameters for graph extraction.
- Portable `.yuxikb.zip` export/import with manifest and checksum validation, followed by Milvus and Neo4j rebuilds.
- PostgreSQL/PostGIS layers, MinIO source objects, layer composition, derived analysis, and MapLibre chat maps.
- Multi-user roles and resource permissions.

## Requirements

- Docker Engine 24+ or Docker Desktop
- Docker Compose v2.20+
- Git
- 16 GB RAM and 20 GB free disk recommended
- Network access and an API key for the selected model provider

## Quick Start

```bash
git clone https://github.com/2233531707/pipeline-k-rag.git
cd pipeline-k-rag
cp .env.template .env
./scripts/init.sh
docker compose config
docker compose up -d --build
docker compose ps
```

Windows PowerShell:

```powershell
git clone https://github.com/2233531707/pipeline-k-rag.git
Set-Location pipeline-k-rag
Copy-Item .env.template .env
.\scripts\init.ps1
docker compose config
docker compose up -d --build
```

At minimum, set a strong `JWT_SECRET_KEY`, a unique `YUXI_INSTANCE_ID`, and a model-provider key. Never commit `.env`.

Default development endpoints:

| Service | URL |
|---|---|
| Web | http://localhost:5173 |
| API docs | http://localhost:5050/docs |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |

The first Web visit guides you through super-administrator initialization.

## Production

```bash
cp .env.template .env.prod
```

Set `YUXI_ENV=production`, strong JWT/PostgreSQL/Neo4j/MinIO secrets, and a unique instance ID. Start with:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

Production Web listens on port 80. Add HTTPS, backups, monitoring, and access control before exposing it publicly.

## Isolated Acceptance Stack

```bash
pnpm --dir web install
pnpm --dir web build
make sync-test-rebuild
make sync-test-status
```

Isolated Web: http://localhost:15173; API: http://localhost:15050.

This stack serves the prebuilt `web/dist` directory through Nginx. Rebuild the frontend after every `web/src` change.

## Tests

```bash
docker compose exec api pytest test/unit -q
docker compose exec api pytest test/integration -q
docker compose exec api ruff check package server test
docker compose exec web pnpm lint
docker compose exec web pnpm test
docker compose exec web pnpm build
```

## Large Data

Uploads and imports use streaming or batching where applicable. Portable knowledge packages are limited to 5 GiB by the backend; Nginx allows 6 GiB for the migration endpoint. Capacity planning and load testing are still required for production document volume and concurrent users.

## Repository Layout

```text
backend/            FastAPI, LangGraph, knowledge services, workers, tests
web/                Vue source and frontend tests
docker/             Images, Nginx, sandbox provisioner, local data volumes
docs/               User and developer documentation
packaging/windows/  Windows launcher and installer sources
scripts/            Initialization and maintenance scripts
```

Local secrets, data volumes, dependencies, build outputs, logs, model files, and `.yuxikb.zip` packages must not be committed.

See [Project Structure](docs/develop-guides/project-structure.md), [Deployment](docs/advanced/deployment.md), and [Architecture](ARCHITECTURE.md).

## License

Licensed under the [MIT License](LICENSE). Required upstream Yuxi and third-party attributions are retained.
