# 💡 Idea Generator for Designers

> "Turn any design challenge into 3 reframes, 3 sketches, and 3 layouts — in seconds."

---

## 🧠 Overview
The **Idea Generator for Designers** is a lightweight AI-powered web app that helps designers rapidly explore creative directions from a single design challenge.

You type a design problem, such as:

> "Improve the bus stop experience."

The app instantly generates:
- ✳️ **3 reframed "How Might We" statements**
- 🎨 **3 conceptual sketch ideas** (visuals generated via DALL·E)
- 🧩 **3 example UI layout suggestions**

It's a tool for **rapid ideation** — helping designers reframe problems, visualize early concepts, and move faster in the creative process.

---

## 🎯 Objectives
Built for the course *AI for Rapid Prototyping*, this project explores:
- How AI can act as a **co-ideator** for creative professionals.  
- How large language and image models can **accelerate early design phases**.  
- How to **prototype AI tools** quickly and locally using Streamlit and OpenAI APIs.

---

## 🧰 Tech Stack

| Layer | Tool | Purpose |
|-------|------|----------|
| **Frontend / UI** | [Streamlit](https://streamlit.io/) | Lightweight Python web framework |
| **Text Generation** | [OpenAI GPT-4](https://platform.openai.com/docs/api-reference) | Creates HMW statements & layout suggestions |
| **Image Generation** | [OpenAI DALL·E 3](https://platform.openai.com/docs/guides/images) | Generates quick conceptual sketches |
| **Local Dev Environment** | [Cursor](https://cursor.sh) | AI-assisted coding, fast iteration |
| **Hosting (optional)** | [Streamlit Community Cloud](https://streamlit.io/cloud) | Free web hosting for demos |

---

## 🔑 Core Feature Groups

- **Problem Reframe Studio**
  - Capture any design brief and instantly generate three fresh “How Might We” statements tuned for different audiences or constraints.
  - Save, edit, or swap statements to explore alternative framing angles before moving forward.
- **Concept Sketch Lab**
  - Translate text concepts into three lightweight visual prompts and DALL·E 3 sketches for quick vibe checks.
  - Export prompts or images to reference boards, whiteboards, or presentation decks.
- **Layout Prototype Deck**
  - Produce three UI layout directions with content structure, interaction notes, and suggested design systems.
  - Streamlined comparisons help decide which concept to explore in high fidelity tools.

---

## 🧩 How It Works

1. **Input:** User enters a design challenge in plain language.
2. **Generation Flow:**
   - GPT-4 reframes the problem into 3 "How Might We" questions.
   - GPT-4 then describes 3 visual sketch ideas (text prompts).
   - DALL·E 3 generates images for those sketches.
   - GPT-4 produces 3 UI layout suggestions for potential digital solutions.
3. **Output:** The app displays all results side-by-side, ready to export or iterate.

---

## 🛠️ Tech Plan

- **Runtime & Hosting**
  - Streamlit app runs locally first, then deploy to Streamlit Cloud for a small group.
- **Frontend Experience**
  - Streamlit UI enhanced with custom CSS, optimized for desktop; stream each section as results arrive for a real-time feel.
- **AI Orchestration**
  - `app.py` coordinates sequential GPT-4 and DALL·E 3 calls using a single backend API key, caching structured responses in memory.
- **Persistence Layer**
  - Lightweight database (SQLite or TinyDB) stores sessions, generated ideas, and timestamps keyed to anonymous session IDs.
- **Export Mechanics**
  - Buttons for copying individual sections plus a “copy all” aggregate export in plain text or markdown.
- **Optional Enhancements**
  - Add authentication later via Streamlit secrets or OAuth; polish responsive layout once the desktop experience is solid.

---

## 🧱 Folder Structure
```
idea-generator/
│
├── app.py # Main Streamlit app
├── prompts/
│   ├── hmw_prompt.txt # prompt template for reframes
│   ├── visual_prompt.txt # prompt template for sketches
│   └── layout_prompt.txt # prompt template for UI ideas
├── utils/
│   ├── openai_helpers.py # functions for GPT/DALL·E calls
│   └── ui_helpers.py # formatting & layout helpers
├── requirements.txt
├── .env # stores your API key
└── assets/
    └── sample_output/ # screenshots for documentation
```
