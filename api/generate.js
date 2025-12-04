// Direct Vercel serverless function for /api/generate

import { generateAll } from '../server/utils/openai-helpers.js'
import { SessionStore } from '../server/utils/session-store.js'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Lazy initialize session store (only when needed)
let sessionStore = null
function getSessionStore() {
  if (!sessionStore) {
    try {
      const dbPath = process.env.VERCEL === '1' || process.env.VERCEL_ENV
        ? '/tmp/sessions.db'
        : join(__dirname, '../data/sessions.db')
      sessionStore = new SessionStore(dbPath)
    } catch (error) {
      console.error('Session store init error:', error)
      sessionStore = {
        createSession: () => {},
        updateSession: () => {},
        getSession: () => null,
        purgeExpiredSessions: () => 0,
      }
    }
  }
  return sessionStore
}

export default async (req, res) => {
  // Always return JSON - set header immediately before any async operations
  res.setHeader('Content-Type', 'application/json')
  
  try {
    console.log('Generate endpoint called:', {
      method: req.method,
      url: req.url,
      hasBody: !!req.body,
      timestamp: new Date().toISOString(),
      cwd: process.cwd(),
      __dirname: __dirname,
    })
    
    if (req.method !== 'POST') {
      return res.status(405).json({ error: 'Method not allowed' })
    }
    
    // Vercel automatically parses JSON bodies
    const { challenge, refineFrom, sessionId } = req.body || {}

    if (!challenge || !challenge.trim()) {
      return res.status(400).json({ error: 'Challenge text is required' })
    }
    
    // Check API key
    const apiKey = process.env.OPENAI_API_KEY
    if (!apiKey) {
      console.error('OPENAI_API_KEY not found in environment')
      return res.status(500).json({ error: 'API key not configured' })
    }

    // Prepare challenge with refinement if provided
    let refinedChallenge = challenge
    if (refineFrom) {
      refinedChallenge = `${challenge}\n\nBuild upon and refine this specific idea: ${refineFrom}\n\nGenerate new ideas that expand and deepen this concept, exploring it from different angles and contexts.`
    }

    console.log('Calling generateAll with challenge length:', refinedChallenge.length)
    // Generate all results
    const results = await generateAll(refinedChallenge)
    console.log('generateAll completed successfully')

    // Persist to database (non-blocking)
    try {
      const store = getSessionStore()
      if (sessionId && store) {
        const existingSession = store.getSession(sessionId)
        if (!existingSession) {
          store.createSession(sessionId, challenge, '', '')
        }

        store.updateSession(sessionId, {
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

    return res.status(200).json({
      hmw: results.hmw,
      feature_ideas: results.feature_ideas,
      user_context: results.user_context,
      sketch_prompts: results.sketch_prompts,
      sketch_concepts: results.sketch_concepts,
      image_urls: results.image_urls || [],
      layouts: results.layouts,
    })
  } catch (error) {
    console.error('=== GENERATION ERROR ===')
    console.error('Error name:', error.name)
    console.error('Error message:', error.message)
    if (error.stack) {
      console.error('Error stack:', error.stack.substring(0, 500))
    }
    if (error.error) {
      console.error('Nested error:', error.error)
    }
    if (error.response) {
      console.error('Response error:', error.response.status, error.response.data)
    }
    if (error.code === 'MODULE_NOT_FOUND') {
      console.error('Module not found - this indicates an import path issue')
    }
    
    // Ensure we return JSON, not HTML
    if (res.headersSent) {
      console.error('Headers already sent, cannot send error response')
      return
    }
    
    let errorMsg = error.message || 'Generation failed'
    if (error.code === 'MODULE_NOT_FOUND') {
      errorMsg = 'Server module not found. Please check deployment configuration.'
    } else if (error.error?.message) {
      errorMsg = error.error.message
    } else if (error.response?.data?.error?.message) {
      errorMsg = error.response.data.error.message
    }
    
    return res.status(500).json({ 
      error: errorMsg,
      type: error.name || 'Error',
      code: error.code
    })
  }
}
