# ─── Build Stage ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# ─── Runtime Stage (nginx for static export) ────────────────────────────────
FROM nginx:alpine AS runner

# Copy static export output
COPY --from=builder /app/out /usr/share/nginx/html

# SPA fallback: redirect all non-asset requests to index.html
# (handles client-side routing for /dashboard/*, /auth/*, etc.)
RUN echo 'server { \
    listen 3000; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /widget { \
        try_files $uri $uri/ /widget/index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]