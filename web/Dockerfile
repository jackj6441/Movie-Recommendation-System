FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json /app/
RUN npm install

COPY vite.config.ts tsconfig.json index.html /app/
COPY public /app/public
COPY src /app/src

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
