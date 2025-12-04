// Vercel serverless function wrapper for Express app
import appModule from '../server/index.js'

const app = appModule.default || appModule

// Export as Vercel serverless function handler
export default (req, res) => {
  // Always set JSON content type first
  if (!res.headersSent) {
    res.setHeader('Content-Type', 'application/json')
  }
  
  try {
    // Log the incoming request for debugging
    console.log('Vercel function called:', {
      method: req.method,
      url: req.url,
      path: req.path || req.url,
      originalUrl: req.originalUrl,
    })
    
    // If app failed to load, return error
    if (!app) {
      console.error('Express app not available')
      return res.status(500).json({ error: 'Server initialization failed' })
    }
    
    // Pass request to Express app
    // Express will handle routing and responses
    return app(req, res)
  } catch (error) {
    console.error('Handler error:', error)
    console.error('Error stack:', error.stack)
    if (!res.headersSent) {
      return res.status(500).json({ 
        error: error.message || 'Internal server error',
        type: error.constructor.name
      })
    }
  }
}
