FROM node:22-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev --no-audit --no-fund --fetch-retries=5 --fetch-retry-mintimeout=2000 --fetch-retry-maxtimeout=20000
COPY requirements.txt ./
RUN pip3 install --break-system-packages --no-cache-dir --retries 5 --timeout 60 -r requirements.txt
COPY server.js ./server.js
COPY bot_template.py ./bot_template.py
COPY public ./public
COPY tests.js ./tests.js
COPY render.yaml ./render.yaml
COPY README.md ./README.md
ENV NODE_ENV=production
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 CMD node -e "require('http').get('http://127.0.0.1:'+(process.env.PORT||3000)+'/api/health',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"
CMD ["node","server.js"]
