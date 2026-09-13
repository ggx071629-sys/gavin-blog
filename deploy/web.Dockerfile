# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS build
WORKDIR /src
COPY package.json package-lock.json ./
COPY packages/contracts ./packages/contracts
COPY apps/web ./apps/web
RUN --mount=type=cache,target=/root/.npm npm ci --include=dev
RUN npm run build:web

FROM node:22-bookworm-slim AS runtime
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
WORKDIR /app
COPY --from=build --chown=node:node /src/apps/web/.output ./
USER node
EXPOSE 3000
CMD ["node", "server/index.mjs"]
