FROM node:22-alpine

WORKDIR /evm
COPY package*.json ./
RUN npm install
COPY contracts ./contracts
COPY scripts ./scripts

CMD ["npm", "run", "deploy"]
