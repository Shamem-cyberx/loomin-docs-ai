FROM node:20-bookworm-slim

WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --omit=dev

COPY server.mjs ./

ENV PORT=1234
EXPOSE 1234

CMD ["node", "server.mjs"]
