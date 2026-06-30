FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@8.15.4 --activate

COPY . /app

RUN pnpm install --frozen-lockfile && \
    pnpm --filter admin build

EXPOSE 3000

CMD ["sh", "-c", "pnpm --dir apps/admin start -- --port ${PORT:-3000}"]
