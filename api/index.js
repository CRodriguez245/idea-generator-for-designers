// Vercel serverless function wrapper for Express app
import app from '../server/index.js'

// Export as Vercel serverless function handler
export default (req, res) => {
  // Ensure we always return JSON
  res.setHeader('Content-Type', 'application/json')
  
  try {
    // Log the incoming request for debugging
    console.log('Vercel function called:', {
      method: req.method,
      url: req.url,
      path: req.path,
      originalUrl: req.originalUrl,
      query: req.query
    })
    
    // Pass request to Express app
    // Express will handle routing and responses
    app(req, res)
  } catch (error) {
    console.error('Handler error:', error)
    if (!res.headersSent) {
      res.status(500).json({ 
        error: error.message || 'Internal server error'
      })
    }
  }
}
