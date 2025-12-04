import OpenAI from 'openai'
import { readFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

let client = null

function getClient() {
  if (!client) {
    const apiKey = process.env.OPENAI_API_KEY
    if (!apiKey) {
      throw new Error(
        'OPENAI_API_KEY not found in environment. Set it in .env file or environment variables.'
      )
    }
    // Validate API key format
    if (!apiKey.startsWith('sk-')) {
      console.warn('Warning: API key does not start with "sk-". This might cause issues.')
    }
    try {
      client = new OpenAI({ apiKey })
    } catch (error) {
      throw new Error(`Failed to initialize OpenAI client: ${error.message}`)
    }
  }
  return client
}

function loadPromptTemplate(templateName) {
  const promptsDir = join(__dirname, '../../prompts')
  const templatePath = join(promptsDir, `${templateName}_prompt.txt`)
  try {
    return readFileSync(templatePath, 'utf-8')
  } catch (error) {
    throw new Error(`Prompt template not found: ${templatePath}`)
  }
}

function fillTemplate(template, challenge) {
  return template.replace(/\{\{challenge\}\}/g, challenge)
}

async function generateHMWStatements(challenge) {
  const client = getClient()
  const template = loadPromptTemplate('hmw')
  const prompt = fillTemplate(template, challenge)

  console.log('Generating HMW statements with model: gpt-4')
  console.log('Challenge length:', challenge.length)
  
  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content:
            "You are a design strategist. Return multiple 'How Might We' statements organized into 3-4 thematic categories. Format as 'Theme 1: [Name]' followed by numbered statements, then 'Theme 2: [Name]', etc.",
        },
        { role: 'user', content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 800,
    })

    const content = response.choices[0].message.content || ''
    return parseHMWThemes(content)
  } catch (error) {
    console.error('HMW generation error:', error)
    console.error('Error type:', error.constructor.name)
    console.error('Error message:', error.message)
    if (error.response) {
      console.error('OpenAI API response:', error.response.data)
    }
    if (error.error) {
      console.error('OpenAI error object:', error.error)
    }
    // Extract the actual error message from OpenAI's error structure
    const errorMsg = error.error?.message || error.message || 'Unknown error'
    throw new Error(`Failed to generate HMW statements: ${errorMsg}`)
  }
}

function parseHMWThemes(content) {
  const themes = {}
  let currentTheme = null
  const lines = content.split('\n')

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    // Check for theme header
    if (trimmed.toLowerCase().startsWith('theme') && trimmed.includes(':')) {
      const parts = trimmed.split(':', 2)
      if (parts.length === 2) {
        currentTheme = parts[1].trim()
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
      }
    } else if (trimmed.includes(':') && !/\d/.test(trimmed.split(':')[0])) {
      const potentialTheme = trimmed.split(':')[0].trim()
      if (potentialTheme.length < 50) {
        currentTheme = potentialTheme
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
      }
    } else if (currentTheme) {
      // Parse HMW statement
      let cleaned = trimmed
      for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-', 'HMW', 'How might we']) {
        if (cleaned.toLowerCase().startsWith(prefix.toLowerCase())) {
          cleaned = cleaned.substring(prefix.length).trim()
          if (cleaned.startsWith(':')) {
            cleaned = cleaned.substring(1).trim()
          }
          break
        }
      }

      if (cleaned && (cleaned.toLowerCase().startsWith('how') || cleaned.length > 10)) {
        if (!cleaned.toLowerCase().startsWith('how might we')) {
          cleaned = `How might we ${cleaned.toLowerCase()}`
        }
        themes[currentTheme].push(cleaned)
      }
    }
  }

  // Fallback if no themes found
  if (Object.keys(themes).length === 0) {
    const statements = content
      .split('\n')
      .filter((line) => {
        const trimmed = line.trim()
        return (
          trimmed &&
          (trimmed.match(/^[1-5]\./) ||
            trimmed.startsWith('•') ||
            trimmed.startsWith('-') ||
            trimmed.toLowerCase().startsWith('hmw') ||
            trimmed.toLowerCase().startsWith('how'))
        )
      })
      .map((stmt) => {
        let cleaned = stmt.trim()
        for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-', 'HMW', 'How might we']) {
          if (cleaned.toLowerCase().startsWith(prefix.toLowerCase())) {
            cleaned = cleaned.substring(prefix.length).trim()
            if (cleaned.startsWith(':')) {
              cleaned = cleaned.substring(1).trim()
            }
            break
          }
        }
        if (cleaned && !cleaned.toLowerCase().startsWith('how might we')) {
          cleaned = `How might we ${cleaned.toLowerCase()}`
        }
        return cleaned
      })
      .filter(Boolean)

    if (statements.length > 0) {
      themes['Reframing'] = statements.slice(0, 4)
      if (statements.length > 4) {
        themes['Exploration'] = statements.slice(4, 8)
      }
      if (statements.length > 8) {
        themes['Innovation'] = statements.slice(8)
      }
    }
  }

  // Ensure we have at least one theme
  if (Object.keys(themes).length === 0) {
    themes['Design Exploration'] = [
      'How might we approach this challenge from a user-centered perspective?',
      'How might we leverage technology to solve this problem?',
      'How might we create sustainable solutions for this challenge?',
    ]
  }

  return themes
}

async function generateSketchPrompts(challenge) {
  const client = getClient()
  const template = loadPromptTemplate('visual')
  const prompt = fillTemplate(template, challenge)

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content:
            'You are a concept artist. Return exactly 3 visual prompt descriptions for DALL·E, one per line, numbered 1-3.',
        },
        { role: 'user', content: prompt },
      ],
      temperature: 0.9,
      max_tokens: 400,
    })

    const content = response.choices[0].message.content || ''
    const prompts = content
      .split('\n')
      .filter((line) => {
        const trimmed = line.trim()
        return (
          trimmed &&
          (/\d/.test(trimmed[0]) || trimmed.startsWith('•') || trimmed.startsWith('-'))
        )
      })
      .map((p) => {
        let cleaned = p.trim()
        for (const prefix of ['1.', '2.', '3.', '•', '-']) {
          if (cleaned.startsWith(prefix)) {
            cleaned = cleaned.substring(prefix.length).trim()
            break
          }
        }
        return cleaned
      })
      .filter(Boolean)

    return prompts.length >= 3 ? prompts.slice(0, 3) : ['sketch prompt 1', 'sketch prompt 2', 'sketch prompt 3']
  } catch (error) {
    throw new Error(`Failed to generate sketch prompts: ${error.message}`)
  }
}

async function generateLayoutSuggestions(challenge) {
  const client = getClient()
  const template = loadPromptTemplate('layout')
  const prompt = fillTemplate(template, challenge)

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content:
            'You are a product designer. Return multiple layout suggestions organized into 3-4 thematic categories. Format as \'Theme 1: [Name]\' followed by numbered layouts with titles and descriptions, then \'Theme 2: [Name]\', etc.',
        },
        { role: 'user', content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 1200,
    })

    const content = response.choices[0].message.content || ''
    return parseLayoutThemes(content)
  } catch (error) {
    throw new Error(`Failed to generate layout suggestions: ${error.message}`)
  }
}

function parseLayoutThemes(content) {
  const themes = {}
  let currentTheme = null
  let currentLayout = null
  const lines = content.split('\n')

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      if (currentLayout && currentTheme && currentLayout.title) {
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
        themes[currentTheme].push(currentLayout)
        currentLayout = null
      }
      continue
    }

    // Check for theme header
    if (trimmed.toLowerCase().startsWith('theme') && trimmed.includes(':')) {
      if (currentLayout && currentTheme && currentLayout.title) {
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
        themes[currentTheme].push(currentLayout)
        currentLayout = null
      }

      const parts = trimmed.split(':', 2)
      if (parts.length === 2) {
        currentTheme = parts[1].trim()
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
      }
    } else if (trimmed.includes(':') && !/\d/.test(trimmed.split(':')[0].substring(0, 10))) {
      const potentialTheme = trimmed.split(':')[0].trim()
      if (potentialTheme.length < 50 && !currentTheme) {
        currentTheme = potentialTheme
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
      } else if (currentTheme && !currentLayout) {
        let title = trimmed
        for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-']) {
          if (title.startsWith(prefix)) {
            title = title.substring(prefix.length).trim()
            break
          }
        }
        currentLayout = { title, description: '' }
      } else if (currentLayout) {
        currentLayout.description += (currentLayout.description ? ' ' : '') + trimmed
      }
    } else if (/\d/.test(trimmed[0]) || trimmed.startsWith('•') || trimmed.startsWith('-')) {
      if (currentLayout && currentTheme && currentLayout.title) {
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
        themes[currentTheme].push(currentLayout)
      }

      let title = trimmed
      for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-']) {
        if (title.startsWith(prefix)) {
          title = title.substring(prefix.length).trim()
          break
        }
      }
      currentLayout = { title, description: '' }
    } else if (currentLayout) {
      currentLayout.description += (currentLayout.description ? ' ' : '') + trimmed
    } else if (currentTheme) {
      currentLayout = { title: trimmed, description: '' }
    }
  }

  // Save last layout
  if (currentLayout && currentTheme && currentLayout.title) {
    if (!themes[currentTheme]) {
      themes[currentTheme] = []
    }
    themes[currentTheme].push(currentLayout)
  }

  // Fallback if no themes found
  if (Object.keys(themes).length === 0) {
    const sections = content.split('\n\n')
    const layoutsList = []
    for (const section of sections) {
      const sectionLines = section.split('\n').map((l) => l.trim()).filter(Boolean)
      if (sectionLines.length > 0) {
        let title = sectionLines[0]
        for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-']) {
          if (title.startsWith(prefix)) {
            title = title.substring(prefix.length).trim()
            break
          }
        }
        const description = sectionLines.slice(1).join(' ') || 'Layout description'
        layoutsList.push({ title, description })
      }
    }

    if (layoutsList.length > 0) {
      themes['Information Architecture'] = layoutsList.slice(0, 3)
      if (layoutsList.length > 3) {
        themes['Interaction Patterns'] = layoutsList.slice(3, 6)
      }
      if (layoutsList.length > 6) {
        themes['Content Strategy'] = layoutsList.slice(6)
      }
    }
  }

  // Ensure we have at least one theme
  if (Object.keys(themes).length === 0) {
    themes['Layout Directions'] = [
      { title: 'Layout 1', description: 'Description 1' },
      { title: 'Layout 2', description: 'Description 2' },
      { title: 'Layout 3', description: 'Description 3' },
    ]
  }

  return themes
}

async function generateImages(prompts) {
  const client = getClient()
  const tasks = prompts.slice(0, 3).map((prompt) =>
    client.images.generate({
      model: 'dall-e-3',
      prompt,
      size: '1024x1024',
      quality: 'standard',
      n: 1,
    })
  )

  try {
    const results = await Promise.allSettled(tasks)
    const images = results.map((result) => {
      if (result.status === 'rejected') {
        return { url: null, revised_prompt: null, error: result.reason?.message }
      }
      if (result.value.data && result.value.data.length > 0) {
        return {
          url: result.value.data[0].url,
          revised_prompt: result.value.data[0].revised_prompt,
        }
      }
      return { url: null, revised_prompt: null }
    })
    return images
  } catch (error) {
    throw new Error(`Failed to generate images: ${error.message}`)
  }
}

async function generateSketchConcepts(challenge, sketchPrompts) {
  const client = getClient()

  const conceptPrompt = `Design challenge: ${challenge}

Three visual sketch concepts have been created for this challenge. For each sketch concept below, provide a brief explanation (1-2 sentences) that describes the DESIGN IDEA or CONCEPT being explored—focus on what design approach or solution concept the image represents, not visual style details.

Sketch concepts:
1. ${sketchPrompts[0] || 'N/A'}
2. ${sketchPrompts[1] || 'N/A'}
3. ${sketchPrompts[2] || 'N/A'}

For each, explain: What design idea or solution approach does this sketch concept explore? What problem does it address or what opportunity does it highlight?

Format as numbered explanations, one per line.`

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content:
            'You are a design strategist. For each sketch concept, provide a clear explanation (1-2 sentences) of the DESIGN IDEA or SOLUTION APPROACH being explored. Focus on what the concept represents conceptually, not visual style. Explain what design problem it addresses or what opportunity it highlights.',
        },
        { role: 'user', content: conceptPrompt },
      ],
      temperature: 0.7,
      max_tokens: 400,
    })

    const content = response.choices[0].message.content || ''
    return parseSketchConcepts(content)
  } catch (error) {
    console.error('Warning: Failed to generate sketch concepts:', error)
    return sketchPrompts.slice(0, 3)
  }
}

function parseSketchConcepts(content) {
  const lines = content.split('\n')
  const explanations = []
  let currentExplanation = null

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      if (currentExplanation) {
        explanations.push(currentExplanation)
        currentExplanation = null
      }
      continue
    }

    if (/\d/.test(trimmed[0]) || trimmed.startsWith('•') || trimmed.startsWith('-')) {
      if (currentExplanation) {
        explanations.push(currentExplanation)
      }

      for (const prefix of ['1.', '2.', '3.', '•', '-']) {
        if (trimmed.startsWith(prefix)) {
          currentExplanation = trimmed.substring(prefix.length).trim()
          break
        }
      }
      if (!currentExplanation) {
        currentExplanation = trimmed
      }
    } else if (currentExplanation) {
      currentExplanation += ' ' + trimmed
    } else {
      currentExplanation = trimmed
    }
  }

  if (currentExplanation) {
    explanations.push(currentExplanation)
  }

  const cleaned = explanations
    .slice(0, 3)
    .map((exp) => exp.trim())
    .filter(Boolean)

  while (cleaned.length < 3) {
    cleaned.push('This sketch explores a design approach for addressing the challenge.')
  }

  return cleaned.slice(0, 3)
}

async function generateFeatureIdeas(challenge) {
  const client = getClient()
  const template = loadPromptTemplate('features')
  const prompt = fillTemplate(template, challenge)

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content:
            'You are a product strategist. Return multiple feature ideas organized into 3-4 thematic categories. Format as \'Theme 1: [Name]\' followed by numbered features with rationale, then \'Theme 2: [Name]\', etc.',
        },
        { role: 'user', content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 1000,
    })

    const content = response.choices[0].message.content || ''
    return parseFeatureThemes(content)
  } catch (error) {
    throw new Error(`Failed to generate feature ideas: ${error.message}`)
  }
}

function parseFeatureThemes(content) {
  const themes = {}
  let currentTheme = null
  const lines = content.split('\n')

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    if (trimmed.toLowerCase().startsWith('theme') && trimmed.includes(':')) {
      const parts = trimmed.split(':', 2)
      if (parts.length === 2) {
        currentTheme = parts[1].trim()
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
      }
    } else if (trimmed.includes(':') && !/\d/.test(trimmed.split(':')[0].substring(0, 10))) {
      const potentialTheme = trimmed.split(':')[0].trim()
      if (potentialTheme.length < 50) {
        currentTheme = potentialTheme
        if (!themes[currentTheme]) {
          themes[currentTheme] = []
        }
      }
    } else if (currentTheme && (/\d/.test(trimmed[0]) || trimmed.startsWith('•') || trimmed.startsWith('-'))) {
      for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-']) {
        if (trimmed.startsWith(prefix)) {
          let featureText = trimmed.substring(prefix.length).trim()
          let feature = featureText
          let rationale = ''

          if (featureText.includes('—')) {
            const parts = featureText.split('—', 2)
            feature = parts[0].trim()
            rationale = parts[1].trim()
          } else if (featureText.includes(' - ')) {
            const parts = featureText.split(' - ', 2)
            feature = parts[0].trim()
            rationale = parts[1].trim()
          }

          themes[currentTheme].push({ feature, rationale })
          break
        }
      }
    }
  }

  // Fallback if no themes found
  if (Object.keys(themes).length === 0) {
    themes['Feature Ideas'] = [
      { feature: 'Feature idea 1', rationale: 'Rationale 1' },
      { feature: 'Feature idea 2', rationale: 'Rationale 2' },
      { feature: 'Feature idea 3', rationale: 'Rationale 3' },
    ]
  }

  return themes
}

async function generateUserContext(challenge) {
  const client = getClient()
  const template = loadPromptTemplate('user_context')
  const prompt = fillTemplate(template, challenge)

  try {
    const response = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content:
            'You are a UX researcher. Return 2-3 user segments, each with a persona and key scenarios. Format as \'User Segment 1: [Name]\' followed by persona description and scenarios, then \'User Segment 2: [Name]\', etc.',
        },
        { role: 'user', content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 800,
    })

    const content = response.choices[0].message.content || ''
    return parseUserSegments(content)
  } catch (error) {
    throw new Error(`Failed to generate user context: ${error.message}`)
  }
}

function parseUserSegments(content) {
  const segments = []
  const parts = content.split('User Segment')

  for (let i = 1; i < parts.length; i++) {
    const part = parts[i]
    const lines = part.split('\n').map((l) => l.trim()).filter(Boolean)
    if (lines.length === 0) continue

    const segmentName = lines[0].includes(':') ? lines[0].split(':', 2)[1].trim() : lines[0]
    const currentSegment = { segment_name: segmentName, persona: null, scenarios: [] }

    let personaStart = null
    let scenariosStart = null
    for (let j = 0; j < lines.length; j++) {
      if (lines[j].toLowerCase().startsWith('persona')) {
        personaStart = j
      } else if (lines[j].toLowerCase().startsWith('key scenarios')) {
        scenariosStart = j
        break
      }
    }

    // Parse persona
    if (personaStart !== null) {
      const endIdx = scenariosStart !== null ? scenariosStart : lines.length
      const personaLines = []
      for (let j = personaStart + 1; j < endIdx; j++) {
        if (lines[j] && !lines[j].toLowerCase().startsWith('key')) {
          personaLines.push(lines[j])
        } else {
          break
        }
      }

      if (personaLines.length > 0) {
        const personaText = personaLines.join(' ')
        const personaName = personaText.includes(':')
          ? personaText.split(':')[0].trim()
          : personaText.split('.')[0].trim()
        currentSegment.persona = { name: personaName, description: personaText }
      }
    }

    // Parse scenarios
    if (scenariosStart !== null) {
      for (let j = scenariosStart + 1; j < lines.length; j++) {
        const line = lines[j]
        if (line.toLowerCase().startsWith('user segment')) {
          break
        }

        for (const prefix of ['1.', '2.', '3.', '4.', '5.', '•', '-']) {
          if (line.startsWith(prefix)) {
            currentSegment.scenarios.push(line.substring(prefix.length).trim())
            break
          }
        }
      }
    }

    if (currentSegment.persona || currentSegment.scenarios.length > 0) {
      segments.push(currentSegment)
    }
  }

  // Fallback if no segments found
  if (segments.length === 0) {
    segments.push({
      segment_name: 'Primary Users',
      persona: { name: 'User', description: 'Primary user persona' },
      scenarios: ['Scenario 1', 'Scenario 2'],
    })
  }

  return segments
}

export async function generateAll(challenge) {
  // Generate all text content in parallel
  const [hmwResults, featureIdeas, sketchPrompts, layouts, userContext] = await Promise.all([
    generateHMWStatements(challenge),
    generateFeatureIdeas(challenge),
    generateSketchPrompts(challenge),
    generateLayoutSuggestions(challenge),
    generateUserContext(challenge),
  ])

  // Then generate images from sketch prompts
  const images = await generateImages(sketchPrompts)

  // Generate conceptual explanations for each sketch
  const sketchConcepts = await generateSketchConcepts(challenge, sketchPrompts)

  return {
    hmw: hmwResults,
    feature_ideas: featureIdeas,
    sketch_prompts: sketchPrompts,
    images: images,
    image_urls: images.map((img) => img.url).filter(Boolean),
    user_context: userContext,
    layouts: layouts,
    sketch_concepts: sketchConcepts,
  }
}

