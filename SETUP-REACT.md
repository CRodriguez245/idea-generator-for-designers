# Quick Setup Guide - React/JavaScript Version

## Prerequisites
- Node.js 18+ installed
- OpenAI API key

## Quick Start

1. **Install dependencies:**

   ```bash
   # Frontend
   cd frontend
   npm install
   cd ..
   
   # Backend
   cd server
   npm install
   cd ..
   ```

2. **Create environment file:**

   Create `server/.env`:
   ```env
   OPENAI_API_KEY=your_key_here
   PORT=5000
   ```

3. **Start the application:**

   **Terminal 1 - Backend:**
   ```bash
   cd server
   npm start
   ```

   **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Open browser:**
   
   Navigate to `http://localhost:3000`

## Development Mode

For auto-reload during development:

**Backend:**
```bash
cd server
npm run dev
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## Troubleshooting

- **Port already in use?** Change `PORT` in `server/.env` or update `vite.config.js` proxy port
- **API errors?** Check that `OPENAI_API_KEY` is set correctly in `server/.env`
- **Module not found?** Run `npm install` in both `frontend/` and `server/` directories

