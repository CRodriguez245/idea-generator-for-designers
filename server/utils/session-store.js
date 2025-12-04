import Database from 'better-sqlite3'
import { existsSync, mkdirSync } from 'fs'
import { dirname } from 'path'

export class SessionStore {
  constructor(databasePath) {
    this.databasePath = databasePath
    
    // Ensure data directory exists
    const dbDir = dirname(databasePath)
    if (!existsSync(dbDir)) {
      mkdirSync(dbDir, { recursive: true })
    }

    this.db = new Database(databasePath)
    this.initSchema()
  }

  initSchema() {
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
    if (this.db) {
      this.db.close()
    }
  }
}

