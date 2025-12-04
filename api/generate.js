// Direct Vercel serverless function for /api/generate
// This avoids the Express routing complexity

import { generateAll } from '../server/utils/openai-helpers.js'
import { SessionStore } from '../server/utils/session-store.js'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Initialize session store
let sessionStore
try {
  const dbPath = process.env.VERCEL === '1' 
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

export default async (req, res) => {
  // Always return JSON
  res.setHeader('Content-Type', 'application/json')
  
  try {
    console.log('Generate endpoint called:', {
      method: req.method,
      url: req.url,
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
      return res.status(500).json({ error: 'API key not configured' })
    }

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

    return res.json({
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
    console.error('Error stack:', error.stack)
    
    let errorMsg = error.message || 'Generation failed'
    if (error.error) {
      errorMsg = error.error.message || errorMsg
    }
    if (error.response?.data?.error) {
      errorMsg = error.response.data.error.message || errorMsg
    }
    
    return res.status(500).json({ error: errorMsg })
  }
}

