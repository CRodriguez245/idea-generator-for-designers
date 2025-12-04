# Deploying to Vercel

## Quick Setup

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Deploy**:
   ```bash
   vercel
   ```

4. **Set Environment Variables**:
   - Go to your Vercel project dashboard
   - Navigate to Settings → Environment Variables
   - Add:
     - `OPENAI_API_KEY` = your OpenAI API key
     - `PORT` = 5001 (optional, Vercel handles this)

5. **Redeploy** after adding environment variables:
   ```bash
   vercel --prod
   ```

## Alternative: Deploy via GitHub Integration

1. **Connect GitHub Repository**:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository

2. **Configure Build Settings**:
   - Root Directory: Leave as root (or set if needed)
   - Build Command: `cd frontend && npm run build`
   - Output Directory: `frontend/dist`
   - Install Command: `cd frontend && npm install && cd ../server && npm install`

3. **Add Environment Variables** (same as above)

4. **Deploy**: Vercel will automatically deploy on every push to main branch

## Project Structure for Vercel

- Frontend builds to `frontend/dist`
- Backend API routes are in `server/` and will be deployed as serverless functions
- API routes are accessible at `/api/*`

## Notes

- The backend Express server will be converted to Vercel serverless functions automatically
- Make sure both `frontend/package.json` and `server/package.json` have all dependencies listed
- Environment variables must be set in Vercel dashboard for the API to work

