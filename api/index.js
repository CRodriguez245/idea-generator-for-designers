// Vercel serverless function wrapper for Express app
import app from '../server/index.js'

// Export as Vercel serverless function handler
// Vercel expects a default export that handles (req, res)
export default (req, res) => {
  // Simply pass the request to Express app
  // Express will handle the response
  return app(req, res)
}

