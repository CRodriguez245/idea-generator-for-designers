import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { generateAll } from './utils/openai-helpers.js'
import { SessionStore } from './utils/session-store.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Load .env from server directory
dotenv.config({ path: join(__dirname, '.env') })

const app = express()
const PORT = process.env.PORT || 5001

// CORS configuration - allow all origins for development
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}))

// Log all requests
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`)
  next()
})


app.use(express.json())

// Initialize session store
const sessionStore = new SessionStore(join(__dirname, '../data/sessions.db'))

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' })
})
app.get('/health', (req, res) => {
  res.json({ status: 'ok' })
})

// Test API key (for debugging)
app.get('/api/test-key', (req, res) => {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey) {
    return res.status(500).json({ error: 'API key not found' })
  }
  res.json({ 
    hasKey: true, 
    keyPrefix: apiKey.substring(0, 7) + '...',
    keyLength: apiKey.length 
  })
})

// Generate endpoint handler
const handleGenerate = async (req, res) => {
  try {
    const { challenge, refineFrom, sessionId } = req.body

    console.log('Received generate request:', { 
      challengeLength: challenge?.length,
      hasRefineFrom: !!refineFrom,
      sessionId 
    })

    if (!challenge || !challenge.trim()) {
      return res.status(400).json({ error: 'Challenge text is required' })
    }
    
    // Check API key
    const apiKey = process.env.OPENAI_API_KEY
    console.log('API Key present:', !!apiKey, 'Key prefix:', apiKey?.substring(0, 10))

    // Prepare challenge with refinement if provided
    let refinedChallenge = challenge
    if (refineFrom) {
      refinedChallenge = `${challenge}\n\nBuild upon and refine this specific idea: ${refineFrom}\n\nGenerate new ideas that expand and deepen this concept, exploring it from different angles and contexts.`
    }

    // Generate all results
    const results = await generateAll(refinedChallenge)

    // Persist to database
    try {
      if (sessionId) {
        const existingSession = sessionStore.getSession(sessionId)
        if (!existingSession) {
          sessionStore.createSession(sessionId, challenge, '', '')
        }

        sessionStore.updateSession(sessionId, {
          hmw_results: results.hmw,
          sketch_prompts: results.sketch_prompts,
          image_urls: results.image_urls || [],
          layout_results: results.layouts,
        })
      }
    } catch (dbError) {
      console.error('Warning: Failed to save to database:', dbError)
      // Don't fail the request if database save fails
    }

    res.json({
      hmw: results.hmw,
      feature_ideas: results.feature_ideas,
      user_context: results.user_context,
      sketch_prompts: results.sketch_prompts,
      sketch_concepts: results.sketch_concepts,
      image_urls: results.image_urls || [],
      layouts: results.layouts,
    })
  } catch (error) {
    console.error('Generation error:', error)
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      cause: error.cause,
      error: error.error,
    })
    
    // Extract error message from OpenAI's error structure
    let errorMsg = error.message || 'Generation failed'
    if (error.error) {
      errorMsg = error.error.message || errorMsg
    }
    if (error.response?.data?.error) {
      errorMsg = error.response.data.error.message || errorMsg
    }
    
    console.error('Final error message:', errorMsg)
    res.status(500).json({ error: errorMsg })
  }
}

// Register generate endpoint
app.post('/api/generate', handleGenerate)
// Also register without /api for Vercel (Vercel adds /api prefix in routing)
app.post('/generate', handleGenerate)

// Purge expired sessions (run on startup)
try {
  const deleted = sessionStore.purgeExpiredSessions()
  if (deleted > 0) {
    console.log(`Purged ${deleted} expired sessions`)
  }
} catch (error) {
  console.error('Warning: Failed to purge expired sessions:', error)
}

// 404 handler
app.use((req, res) => {
  console.log(`404 - Route not found: ${req.method} ${req.path}`)
  res.status(404).json({ error: 'Route not found', path: req.path, method: req.method })
})

// Error handler
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err)
  if (!res.headersSent) {
    res.status(500).json({ error: err.message || 'Internal server error' })
  }
})

// Only start server if not in Vercel environment
if (process.env.VERCEL !== '1') {
  app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`)
  })
}

// Export for Vercel serverless
export default app

