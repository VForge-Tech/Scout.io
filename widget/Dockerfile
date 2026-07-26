FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM scratch AS artifact

COPY --from=builder /app/dist /dist
