FROM node:22-alpine
WORKDIR /app
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ .
RUN npm run build
EXPOSE 5000
CMD ["npm", "start"]
