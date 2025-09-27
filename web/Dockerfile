FROM node:20-alpine

WORKDIR /app/web

COPY package*.json .

RUN npm install -g @angular/cli

RUN npm install --legacy-peer-deps

COPY . .
