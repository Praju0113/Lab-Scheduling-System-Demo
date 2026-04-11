FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Expose the development server port
EXPOSE 5173

# Run dev server with host 0.0.0.0 to make it accessible from outside container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
