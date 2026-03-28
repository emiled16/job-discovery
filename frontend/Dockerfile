FROM node:24-alpine AS deps

WORKDIR /app

COPY package.json ./
RUN npm install

FROM node:24-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runner

ENV NODE_ENV=production

WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/scripts ./scripts

USER appuser

EXPOSE 3000

CMD ["sh", "-c", "node ./scripts/validate-config.mjs && node server.js"]
