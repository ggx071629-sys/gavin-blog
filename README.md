# Gavin Blog

Business source for the Gavin blog and question-answering assistant.

- `apps/web/`: Nuxt pages, components, server proxy, and static assets.
- `apps/api/app/`: FastAPI business logic, assistant, index Worker, and E5 service code.
- `apps/api/migrations/`: content database migrations.
- `apps/api/assistant_runtime_migrations/`: assistant runtime database migrations.
- `apps/api/embedding_service/`: separate E5 environment dependency manifest and lockfile.
- `apps/api/scripts/`: contract export, model preparation, provisioning, service entry points, qualification, and backup utilities.
- `packages/contracts/`: OpenAPI contract and generated TypeScript types.

Dependency manifests and lockfiles are committed. Installed dependencies, model weights, real environment files, credentials, databases, and uploaded media are excluded.

Run `npm ci` and `npm run build:web` from the repository root to build the frontend. Python dependencies are managed separately with uv in the API and E5 environment directories.

Docker and production deployment configuration will be added separately. An empty installation still requires database initialization, production secrets, model preparation, indexing, and assistant production qualification before public enablement.
