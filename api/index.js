// Vercel serverless function wrapper for Express app
import app from '../server/index.js'

// Export as Vercel serverless function handler
// Vercel expects a default export that handles (req, res)
export default async (req, res) => {
  // Handle the request with Express app
  app(req, res)
}

