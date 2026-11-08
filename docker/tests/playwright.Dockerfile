FROM docker.io/library/node:22.23.4-bookworm-slim@sha256:aaa4b5baf1ecff3b283486bb1f90405cdda225a3e6f79660d2c559fa510a7292 AS dependencies
WORKDIR /tests
COPY tests/e2e/package.json tests/e2e/package-lock.json ./
RUN npm install --global npm@12.2.2 && npm ci --no-audit --no-fund
FROM mcr.microsoft.com/playwright:v1.56.1-noble@sha256:42f02d323c310069b4d54c94bd91a608966a486c3492c48ae0b1cea747ec5ca2
COPY docker/tests/os-packages.lock /opt/aat/os-packages.lock
RUN apt-get update && sed "/^#/d;/^$/d" /opt/aat/os-packages.lock | xargs apt-get install -y --no-install-recommends && rm -rf /var/lib/apt/lists/* /usr/lib/node_modules/npm && rm -f /usr/bin/npm /usr/bin/npx
WORKDIR /tests
COPY --from=dependencies /tests/node_modules ./node_modules
COPY tests/e2e ./
ENV PLAYWRIGHT_BASE_URL=http://frontend:80
CMD ["node", "node_modules/@playwright/test/cli.js", "test"]
