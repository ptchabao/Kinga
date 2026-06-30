FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@8.15.4 --activate

COPY . /app

RUN pnpm install --frozen-lockfile && \
    pnpm --dir apps/onprem-dashboard build

EXPOSE 3002

CMD ["sh", "-c", "pnpm --dir apps/onprem-dashboard start -- --port ${PORT:-3002}"]
