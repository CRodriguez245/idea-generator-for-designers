# 💡 Idea Generator for Designers (React/JavaScript Version)

> "Turn any design challenge into 3 reframes, 3 sketches, and 3 layouts — in seconds."

This is the React/JavaScript/Tailwind CSS version of the Idea Generator for Designers, converted from the original Streamlit/Python implementation.

---

## 🧠 Overview

The **Idea Generator for Designers** is a lightweight AI-powered web app that helps designers rapidly explore creative directions from a single design challenge.

You type a design problem, such as:

> "Improve the bus stop experience."

The app instantly generates:
- ✳️ **Multiple "How Might We" statements** organized by theme
- 🎨 **3 conceptual sketch ideas** (visuals generated via DALL·E)
- 🧩 **Multiple UI layout suggestions** organized by theme
- 👥 **User personas and scenarios**
- 💡 **Feature ideas** organized by theme

It's a tool for **rapid ideation** — helping designers reframe problems, visualize early concepts, and move faster in the creative process.

---

## 🧰 Tech Stack

| Layer | Tool | Purpose |
|-------|------|----------|
| **Frontend** | React 18 + Vite | Modern React application |
| **Styling** | Tailwind CSS | Utility-first CSS framework |
| **Backend** | Node.js + Express | REST API server |
| **Text Generation** | OpenAI GPT-4 | Creates HMW statements, features, layouts, user context |
| **Image Generation** | OpenAI DALL·E 3 | Generates quick conceptual sketches |
| **Database** | SQLite (better-sqlite3) | Session persistence |

---

## 🚀 Setup & Installation

### Prerequisites

- Node.js 18+ and npm
- OpenAI API key

### Installation Steps

1. **Clone or navigate to the project directory**

2. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Install backend dependencies:**
   ```bash
   cd server
   npm install
   cd ..
   ```

4. **Set up environment variables:**
   
   Create a `.env` file in the `server/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   PORT=5000
   ```

5. **Start the backend server:**
   ```bash
   cd server
   npm start
   # Or for development with auto-reload:
   npm run dev
   ```

   The server will run on `http://localhost:5000`

6. **Start the frontend development server:**
   
   In a new terminal:
   ```bash
   cd frontend
   npm run dev
   ```

   The frontend will run on `http://localhost:3000` and proxy API requests to the backend.

7. **Open your browser:**
   
   Navigate to `http://localhost:3000` to use the application.

---

## 📁 Project Structure

```
idea-generator-for-designers/
│
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── App.jsx       # Main application component
│   │   ├── main.jsx      # React entry point
│   │   └── index.css     # Tailwind CSS styles
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── server/                # Node.js/Express backend
│   ├── index.js          # Express server entry point
│   ├── utils/
│   │   ├── openai-helpers.js    # OpenAI API integration
│   │   └── session-store.js     # SQLite session persistence
│   └── package.json
│
├── prompts/              # Prompt templates (shared)
│   ├── hmw_prompt.txt
│   ├── visual_prompt.txt
│   ├── layout_prompt.txt
│   ├── features_prompt.txt
│   └── user_context_prompt.txt
│
├── data/                 # Database storage
│   └── sessions.db      # SQLite database (created automatically)
│
└── .env                  # Environment variables (create this)
```

---

## 🔑 Core Features

- **Problem Reframe Studio**
  - Capture any design brief and instantly generate multiple "How Might We" statements organized by theme
  - Select and build upon specific ideas

- **Concept Sketch Lab**
  - Translate text concepts into visual prompts and DALL·E 3 sketches
  - View conceptual explanations for each sketch

- **Layout Prototype Deck**
  - Produce multiple UI layout directions organized by theme
  - Each layout includes title, description, and interaction notes

- **User Context**
  - Generate user personas and key scenarios for different user segments

- **Feature Ideas**
  - Generate feature ideas organized by theme with rationale

- **Build on Selected Ideas**
  - Select multiple ideas across different sections
  - Build upon selected ideas to generate refined concepts

- **Session Persistence**
  - Automatically saves sessions to SQLite database
  - Sessions are retained for 180 days

---

## 🧩 How It Works

1. **Input:** User enters a design challenge in plain language.
2. **Generation Flow:**
   - GPT-4 generates HMW statements, feature ideas, sketch prompts, layouts, and user context in parallel
   - DALL·E 3 generates images for the sketch prompts
   - GPT-4 generates conceptual explanations for each sketch
3. **Output:** The app displays all results in organized tabs, ready to explore and iterate.

---

## 🔧 Development

### Frontend Development

```bash
cd frontend
npm run dev
```

The frontend uses:
- **React 18** with hooks for state management
- **Vite** for fast development and building
- **Tailwind CSS** for styling (matching the original ResearchBridge-inspired design)

### Backend Development

```bash
cd server
npm run dev  # Auto-reloads on file changes
```

The backend provides:
- REST API endpoints for generation
- Session management with SQLite
- Error handling and rate limit management

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`

**Backend:**
The backend can be run directly with Node.js or deployed to services like:
- Heroku
- Railway
- Render
- AWS Lambda (with modifications)

---

## 🔐 Environment Variables

Create a `.env` file in the `server/` directory:

```env
OPENAI_API_KEY=sk-...
PORT=5000
```

---

## 📝 API Endpoints

### `POST /api/generate`

Generate all ideas for a design challenge.

**Request Body:**
```json
{
  "challenge": "Improve the bus stop experience for commuters during winter storms.",
  "refineFrom": "Optional: Build upon and expand these ideas...",
  "sessionId": "optional-session-id"
}
```

**Response:**
```json
{
  "hmw": { "Theme 1": ["HMW statement 1", ...], ... },
  "feature_ideas": { "Theme 1": [{ "feature": "...", "rationale": "..." }], ... },
  "user_context": [{ "segment_name": "...", "persona": {...}, "scenarios": [...] }, ...],
  "sketch_prompts": ["prompt 1", "prompt 2", "prompt 3"],
  "sketch_concepts": ["concept 1", "concept 2", "concept 3"],
  "image_urls": ["url1", "url2", "url3"],
  "layouts": { "Theme 1": [{ "title": "...", "description": "..." }], ... }
}
```

### `GET /api/health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

---

## 🎨 Styling

The application uses Tailwind CSS with custom configuration to match the original ResearchBridge-inspired design:

- **Typography:** Futura for headers, Helvetica for body text
- **Colors:** Blue primary color (#1976d2), clean grays
- **Layout:** Centered, max-width container (900px)
- **Components:** Custom button styles, input fields, result sections

---

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"
- Make sure you've created a `.env` file in the `server/` directory
- Ensure the file contains `OPENAI_API_KEY=your_key_here`

### "Cannot connect to API"
- Make sure the backend server is running on port 5000
- Check that the frontend proxy is configured correctly in `vite.config.js`

### "Rate limit reached"
- OpenAI API has rate limits. Wait a moment and try again.
- Consider upgrading your OpenAI plan if you hit limits frequently.

### Database errors
- The SQLite database is created automatically in `data/sessions.db`
- Make sure the `data/` directory exists and is writable

---

## 📄 License

Same as the original project.

---

## 🙏 Acknowledgments

This React/JavaScript version maintains the same functionality and design philosophy as the original Streamlit/Python version, providing a modern web development stack alternative.

