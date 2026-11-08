FROM mcr.microsoft.com/playwright:v1.65.0-resolute@sha256:fb9978a801599ea0a57079eb642ad75cb52dbe1b162c8bf1fc989a603aa39218 AS dependencies
WORKDIR /tests
RUN npm init -y && npm install --save-exact @playwright/test@1.65.0
FROM mcr.microsoft.com/playwright:v1.65.0-resolute@sha256:fb9978a801599ea0a57079eb642ad75cb52dbe1b162c8bf1fc989a603aa39218
WORKDIR /tests
COPY --from=dependencies /tests/ ./
COPY tests/e2e/*.ts ./
RUN apt-get update && apt-get install -y --no-install-recommends apt=3.2.1ubuntu0.1 libapt-pkg7.0=3.2.1ubuntu0.1 && rm -rf /var/lib/apt/lists/*
RUN rm -rf /usr/lib/node_modules/npm /usr/local/lib/node_modules/npm && rm -f /usr/bin/npm /usr/bin/npx /usr/local/bin/npm /usr/local/bin/npx
CMD ["node","node_modules/@playwright/test/cli.js","test"]
