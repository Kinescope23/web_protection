FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./

#ИСПРАВЛЕНИЕ: Очистка кэша и установка без опциональных зависимостей предотвращает ETXTBSY
RUN npm cache clean --force && npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]