FROM --platform=linux/amd64 node:20-alpine AS builder
WORKDIR /app

# Accept build-time argument
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM --platform=linux/amd64 node:20-alpine
WORKDIR /app

# Copy everything from builder
COPY --from=builder /app ./

# Clean up dev dependencies and reinstall only production deps
RUN rm -rf node_modules && npm ci --omit=dev

ENV NODE_ENV=production

CMD ["sh", "-c", "npm run start -- -p ${PORT:-3000}"]