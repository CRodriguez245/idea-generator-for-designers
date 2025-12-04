import { existsSync, mkdirSync } from 'fs'
import { dirname } from 'path'

export class SessionStore {
  constructor(databasePath) {
    this.databasePath = databasePath
    
    // Always use in-memory on Vercel (better-sqlite3 doesn't build there)
    if (process.env.VERCEL === '1' || process.env.VERCEL_ENV) {
      this.inMemory = true
      this.sessions = new Map()
      console.log('Using in-memory session store (Vercel/serverless mode)')
      return
    }
    
    // Try to use better-sqlite3 for local development only
    // Skip entirely on Vercel to avoid any import issues
    this.inMemory = true
    this.sessions = new Map()
    
    // Only try to use SQLite locally (not on Vercel)
    if (process.env.VERCEL !== '1' && !process.env.VERCEL_ENV) {
      // Try dynamic import asynchronously (non-blocking)
      import('better-sqlite3').then(({ default: Database }) => {
        try {
          this.inMemory = false
          
          // Ensure data directory exists
          const dbDir = dirname(databasePath)
          if (!existsSync(dbDir)) {
            mkdirSync(dbDir, { recursive: true })
          }

          this.db = new Database(databasePath)
          this.initSchema()
          console.log('Using SQLite database for sessions')
        } catch (dbError) {
          console.warn('Failed to initialize SQLite, using in-memory:', dbError.message)
          this.inMemory = true
        }
      }).catch(() => {
        // better-sqlite3 not available, already using in-memory
        console.log('better-sqlite3 not available, using in-memory store')
      })
    }
  }

  initSchema() {
    if (this.inMemory || !this.db) return
    
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        user_name TEXT,
        user_email TEXT,
        challenge_text TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        hmw_results TEXT,
        sketch_prompts TEXT,
        image_urls TEXT,
        layout_results TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_session_id ON sessions(session_id);
      CREATE INDEX IF NOT EXISTS idx_created_at ON sessions(created_at);
    `)
  }

  createSession(sessionId, challengeText, userName = '', userEmail = '') {
    try {
      if (this.inMemory) {
        this.sessions.set(sessionId, {
          session_id: sessionId,
          challenge_text: challengeText,
          user_name: userName || null,
          user_email: userEmail || null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        return sessionId
      }
      
      if (!this.db) {
        // Fallback to in-memory if db not ready
        this.inMemory = true
        if (!this.sessions) this.sessions = new Map()
        return this.createSession(sessionId, challengeText, userName, userEmail)
      }
      
      const stmt = this.db.prepare(`
        INSERT INTO sessions (session_id, challenge_text, user_name, user_email)
        VALUES (?, ?, ?, ?)
      `)
      stmt.run(sessionId, challengeText, userName || null, userEmail || null)
      return sessionId
    } catch (error) {
      throw new Error(`Failed to create session: ${error.message}`)
    }
  }

  updateSession(sessionId, payload) {
    try {
      if (this.inMemory) {
        const session = this.sessions.get(sessionId)
        if (!session) {
          throw new Error(`Session not found: ${sessionId}`)
        }
        
        if (payload.hmw_results !== undefined) {
          session.hmw_results = JSON.stringify(payload.hmw_results)
        }
        if (payload.sketch_prompts !== undefined) {
          session.sketch_prompts = JSON.stringify(payload.sketch_prompts)
        }
        if (payload.image_urls !== undefined) {
          session.image_urls = JSON.stringify(payload.image_urls)
        }
        if (payload.layout_results !== undefined) {
          session.layout_results = JSON.stringify(payload.layout_results)
        }
        session.updated_at = new Date().toISOString()
        return
      }
      
      if (!this.db) {
        this.inMemory = true
        if (!this.sessions) this.sessions = new Map()
        return this.updateSession(sessionId, payload)
      }
      
      const updates = []
      const values = []

      if (payload.hmw_results !== undefined) {
        updates.push('hmw_results = ?')
        values.push(JSON.stringify(payload.hmw_results))
      }
      if (payload.sketch_prompts !== undefined) {
        updates.push('sketch_prompts = ?')
        values.push(JSON.stringify(payload.sketch_prompts))
      }
      if (payload.image_urls !== undefined) {
        updates.push('image_urls = ?')
        values.push(JSON.stringify(payload.image_urls))
      }
      if (payload.layout_results !== undefined) {
        updates.push('layout_results = ?')
        values.push(JSON.stringify(payload.layout_results))
      }

      if (updates.length === 0) {
        return
      }

      updates.push('updated_at = CURRENT_TIMESTAMP')
      values.push(sessionId)

      const stmt = this.db.prepare(`
        UPDATE sessions
        SET ${updates.join(', ')}
        WHERE session_id = ?
      `)
      const result = stmt.run(...values)

      if (result.changes === 0) {
        throw new Error(`Session not found: ${sessionId}`)
      }
    } catch (error) {
      throw new Error(`Failed to update session: ${error.message}`)
    }
  }

  getSession(sessionId) {
    try {
      if (this.inMemory) {
        const session = this.sessions.get(sessionId)
        if (!session) {
          return null
        }
        
        return {
          session_id: session.session_id,
          user_name: session.user_name,
          user_email: session.user_email,
          challenge_text: session.challenge_text,
          hmw_results: session.hmw_results ? JSON.parse(session.hmw_results) : [],
          sketch_prompts: session.sketch_prompts ? JSON.parse(session.sketch_prompts) : [],
          image_urls: session.image_urls ? JSON.parse(session.image_urls) : [],
          layout_results: session.layout_results ? JSON.parse(session.layout_results) : [],
          created_at: session.created_at,
        }
      }
      
      if (!this.db) {
        this.inMemory = true
        if (!this.sessions) this.sessions = new Map()
        return this.getSession(sessionId)
      }
      
      const stmt = this.db.prepare('SELECT * FROM sessions WHERE session_id = ?')
      const row = stmt.get(sessionId)

      if (!row) {
        return null
      }

      return {
        session_id: row.session_id,
        user_name: row.user_name,
        user_email: row.user_email,
        challenge_text: row.challenge_text,
        hmw_results: row.hmw_results ? JSON.parse(row.hmw_results) : [],
        sketch_prompts: row.sketch_prompts ? JSON.parse(row.sketch_prompts) : [],
        image_urls: row.image_urls ? JSON.parse(row.image_urls) : [],
        layout_results: row.layout_results ? JSON.parse(row.layout_results) : [],
        created_at: row.created_at,
      }
    } catch (error) {
      throw new Error(`Failed to get session: ${error.message}`)
    }
  }

  purgeExpiredSessions(retentionDays = 180) {
    try {
      if (this.inMemory) {
        const cutoff = new Date()
        cutoff.setDate(cutoff.getDate() - retentionDays)
        let deleted = 0
        for (const [sessionId, session] of this.sessions.entries()) {
          if (new Date(session.created_at) < cutoff) {
            this.sessions.delete(sessionId)
            deleted++
          }
        }
        return deleted
      }
      
      if (!this.db) return 0
      
      const stmt = this.db.prepare(`
        DELETE FROM sessions
        WHERE created_at < datetime('now', '-' || ? || ' days')
      `)
      const result = stmt.run(retentionDays)
      return result.changes
    } catch (error) {
      throw new Error(`Failed to purge expired sessions: ${error.message}`)
    }
  }

  close() {
    if (this.db && !this.inMemory) {
      this.db.close()
    }
  }
}
