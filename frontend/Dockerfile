# Use an official Node runtime as a parent image
FROM node:20-bullseye-slim as build
WORKDIR '/app'
COPY package.json ./
RUN npm install
COPY . ./
RUN npm run build

# Stage 2: Use NGINX to serve the built files
FROM nginx

COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=build /app/nginx.conf /etc/nginx/conf.d/default.conf

