# The "web" image: Caddy serving the built React app and proxying /api to FastAPI.
# Build from the repo root:  docker build -f deploy/web.Dockerfile -t app-web .
FROM node:24-slim AS build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2
COPY --from=build /frontend/dist /srv
# The Caddyfile is mounted at runtime (cloud or lan variant), see docker-compose.yml.
