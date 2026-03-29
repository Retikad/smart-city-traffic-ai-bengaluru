FROM node:18-alpine AS build
WORKDIR /app

# Install dependencies and build
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build

FROM node:18-alpine
WORKDIR /app

# lightweight static server
RUN npm install -g serve --silent
COPY --from=build /app/build ./build

EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
