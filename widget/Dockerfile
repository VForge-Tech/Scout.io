FROM node:20-alpine AS builder

WORKDIR /app

COPY widget/package*.json ./
RUN npm ci

COPY widget/ .
RUN npm run build

FROM scratch AS artifact

COPY --from=builder /app/dist /dist
