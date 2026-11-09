FROM docker.io/library/node:22.23.4-bookworm-slim@sha256:aaa4b5baf1ecff3b283486bb1f90405cdda225a3e6f79660d2c559fa510a7292 AS dependencies
WORKDIR /tests
COPY tests/e2e/package.json tests/e2e/package-lock.json ./
RUN npm install --global npm@12.2.2 && npm ci --no-audit --no-fund
FROM mcr.microsoft.com/playwright:v1.65.0-resolute@sha256:fb9978a801599ea0a57079eb642ad75cb52dbe1b162c8bf1fc989a603aa39218
COPY docker/tests/os-packages.lock /opt/aat/os-packages.lock
RUN apt-get update && sed "/^#/d;/^$/d" /opt/aat/os-packages.lock | xargs apt-get install -y --no-install-recommends && rm -rf /var/lib/apt/lists/* /usr/lib/node_modules/npm /usr/local/lib/node_modules/npm && rm -f /usr/bin/npm /usr/bin/npx /usr/local/bin/npm /usr/local/bin/npx
WORKDIR /tests
COPY --from=dependencies /tests/node_modules ./node_modules
COPY tests/e2e ./
ENV PLAYWRIGHT_BASE_URL=http://frontend:80
CMD ["node", "node_modules/@playwright/test/cli.js", "test"]
