FROM node:20 AS build
WORKDIR /app
COPY web-console/package*.json ./
RUN npm install
COPY web-console /app
RUN npm run build

FROM nginx:1.27
COPY deploy/docker/web-console.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
