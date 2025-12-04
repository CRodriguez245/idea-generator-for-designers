import { useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'

function App() {
  const [challengeText, setChallengeText] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [generationComplete, setGenerationComplete] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [originalChallenge, setOriginalChallenge] = useState('')
  
  // Results state
  const [hmwResults, setHmwResults] = useState({})
  const [featureIdeas, setFeatureIdeas] = useState({})
  const [userContext, setUserContext] = useState([])
  const [sketchPrompts, setSketchPrompts] = useState([])
  const [sketchConcepts, setSketchConcepts] = useState([])
  const [imageUrls, setImageUrls] = useState([])
  const [layoutResults, setLayoutResults] = useState({})
  
  // Selection and history
  const [selectedIdeas, setSelectedIdeas] = useState([])
  const [ideaTexts, setIdeaTexts] = useState({})
  const [historyStack, setHistoryStack] = useState([])
  const [currentRefinement, setCurrentRefinement] = useState(null)
  const [activeTab, setActiveTab] = useState('hmw')
  const [isRefinementExpanded, setIsRefinementExpanded] = useState(false)

  // Initialize session ID
  useEffect(() => {
    if (!sessionId) {
      setSessionId(uuidv4())
    }
  }, [sessionId])

  const saveStateToHistory = () => {
    const historyEntry = {
      hmwResults,
      featureIdeas,
      userContext,
      sketchPrompts,
      sketchConcepts,
      layoutResults,
      imageUrls,
      currentRefinement,
      challengeText,
    }
    setHistoryStack([...historyStack, historyEntry])
  }

  const restoreStateFromHistory = () => {
    if (historyStack.length === 0) return
    
    const previousState = historyStack[historyStack.length - 1]
    setHmwResults(previousState.hmwResults || {})
    setFeatureIdeas(previousState.featureIdeas || {})
    setUserContext(previousState.userContext || [])
    setSketchPrompts(previousState.sketchPrompts || [])
    setSketchConcepts(previousState.sketchConcepts || [])
    setLayoutResults(previousState.layoutResults || {})
    setImageUrls(previousState.imageUrls || [])
    setCurrentRefinement(previousState.currentRefinement)
    setChallengeText(previousState.challengeText || '')
    setGenerationComplete(true)
    setHistoryStack(historyStack.slice(0, -1))
  }

  const handleGenerate = async () => {
    if (!challengeText.trim() || isGenerating) return

    setIsGenerating(true)
    setErrorMessage('')
    setGenerationComplete(false)
    setHistoryStack([])
    setCurrentRefinement(null)
    setIsRefinementExpanded(false)
    setOriginalChallenge(challengeText)
    setSelectedIdeas([])
    setIdeaTexts({})

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          challenge: challengeText,
          sessionId: sessionId,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Generation failed')
      }

      const data = await response.json()
      
      setHmwResults(data.hmw || {})
      setFeatureIdeas(data.feature_ideas || {})
      setUserContext(data.user_context || [])
      setSketchPrompts(data.sketch_prompts || [])
      setSketchConcepts(data.sketch_concepts || data.sketch_prompts || [])
      setImageUrls(data.image_urls || [])
      setLayoutResults(data.layouts || {})
      setGenerationComplete(true)
      setErrorMessage('')
    } catch (error) {
      let errorMsg = error.message
      if (errorMsg.toLowerCase().includes('rate limit') || errorMsg.includes('429')) {
        errorMsg = 'Rate limit reached. Please wait a moment and try again.'
      } else if (errorMsg.includes('API key') || errorMsg.includes('OPENAI_API_KEY')) {
        errorMsg = 'API key not configured. Please set OPENAI_API_KEY in your .env file.'
      }
      setErrorMessage(errorMsg)
      setGenerationComplete(false)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleBuildOnSelected = async () => {
    if (selectedIdeas.length === 0) return

    const selectedTexts = selectedIdeas
      .map(id => ideaTexts[id])
      .filter(Boolean)

    if (selectedTexts.length === 0) {
      setErrorMessage('No valid ideas found in selection')
      return
    }

    saveStateToHistory()

    const ideasText = selectedTexts.map(idea => `- ${idea}`).join('\n')
    const combinedRefinement = `Build upon and expand these ideas:\n${ideasText}`
    const challenge = originalChallenge || challengeText

    setIsGenerating(true)
    setErrorMessage('')
    setCurrentRefinement(combinedRefinement)
    setIsRefinementExpanded(false)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          challenge: challenge,
          refineFrom: combinedRefinement,
          sessionId: sessionId,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Refinement failed')
      }

      const data = await response.json()
      
      setHmwResults(data.hmw || {})
      setFeatureIdeas(data.feature_ideas || {})
      setUserContext(data.user_context || [])
      setSketchPrompts(data.sketch_prompts || [])
      setSketchConcepts(data.sketch_concepts || data.sketch_prompts || [])
      setImageUrls(data.image_urls || [])
      setLayoutResults(data.layouts || {})
      setGenerationComplete(true)
      setErrorMessage('')
      setSelectedIdeas([])
      setIdeaTexts({})
    } catch (error) {
      let errorMsg = error.message
      if (errorMsg.toLowerCase().includes('rate limit') || errorMsg.includes('429')) {
        errorMsg = 'Rate limit reached. Please wait a moment and try again.'
      } else {
        errorMsg = `Refinement failed: ${errorMsg}`
      }
      setErrorMessage(errorMsg)
      setGenerationComplete(false)
    } finally {
      setIsGenerating(false)
    }
  }

  const toggleIdeaSelection = (ideaId, ideaText) => {
    if (selectedIdeas.includes(ideaId)) {
      setSelectedIdeas(selectedIdeas.filter(id => id !== ideaId))
      const newTexts = { ...ideaTexts }
      delete newTexts[ideaId]
      setIdeaTexts(newTexts)
    } else {
      setSelectedIdeas([...selectedIdeas, ideaId])
      setIdeaTexts({ ...ideaTexts, [ideaId]: ideaText })
    }
  }

  const hasResults = generationComplete || Object.keys(hmwResults).length > 0

  return (
    <div className="h-screen bg-white flex overflow-hidden">
      {/* Left Sidebar */}
      <div className="w-80 border-r border-gray-200 bg-gray-50 p-6 flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-futura text-black mb-1">Idea Generator for Designers</h1>
          <p className="text-sm text-gray-600 mt-1">
            Turn a single design challenge into reframes, sketches, and layout.
          </p>
        </div>

        {/* Design Challenge Section */}
        <div className="flex-1">
          <h2 className="text-lg font-futura text-black mb-2">Design Challenge</h2>
          <p className="text-sm text-gray-600 mb-4">
            Choose what you want to do. Enter your design challenge below to
          </p>

          <textarea
            className="textarea-field w-full"
            value={challengeText}
            onChange={(e) => setChallengeText(e.target.value)}
            placeholder="Improve the bus stop experience for commuters during winter storms."
            rows={4}
          />

          <div className="mt-4">
            <button
              className="btn-primary w-full"
              onClick={handleGenerate}
              disabled={isGenerating || !challengeText.trim()}
            >
              Generate Concepts
            </button>
            {isGenerating && (
              <button
                className="btn-secondary w-full mt-2"
                onClick={() => {
                  setIsGenerating(false)
                  setGenerationComplete(false)
                  setErrorMessage('Generation was cancelled.')
                }}
              >
                Cancel Generation
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Right Main Panel */}
      <div className="flex-1 overflow-y-auto h-screen">
        <div className="max-w-5xl mx-auto px-8 py-8">
          {/* Results Overview */}
          <h2 className="text-2xl font-futura text-black mb-2">Results Overview</h2>
          <p className="section-description">
            Review the generated reframes, sketches, and layout ideas below.
          </p>

        {/* Error Message */}
        {errorMessage && (
          <div className="error-box mb-4">{errorMessage}</div>
        )}

        {/* Loading State */}
        {isGenerating && !hasResults && (
          <>
            <div className="info-box mb-4">
              Generating ideas... This may take 30-60 seconds. Please be patient.
            </div>
            <div className="warning-box">
              If this takes longer than 2 minutes, click 'Cancel Generation' and try again.
            </div>
          </>
        )}

        {/* Results */}
        {hasResults && !isGenerating && (
          <>
            {/* Back Button and Refinement Indicator */}
            {(historyStack.length > 0 || currentRefinement) && (
              <div className="mb-4 flex gap-4 items-start">
                <button
                  className="btn-secondary"
                  onClick={restoreStateFromHistory}
                  disabled={historyStack.length === 0}
                >
                  ← Back
                </button>
                {currentRefinement && (
                  <div className="info-box flex-1">
                    <div className="flex items-start gap-2">
                      <div className="flex-1">
                        <strong>Currently building on:</strong>{' '}
                        {isRefinementExpanded ? (
                          <span>{currentRefinement}</span>
                        ) : (
                          <span>
                            {currentRefinement.length > 100
                              ? `${currentRefinement.substring(0, 100)}...`
                              : currentRefinement}
                          </span>
                        )}
                      </div>
                      {currentRefinement.length > 100 && (
                        <button
                          onClick={() => setIsRefinementExpanded(!isRefinementExpanded)}
                          className="text-primary hover:text-primary-dark text-sm font-medium ml-2 whitespace-nowrap"
                        >
                          {isRefinementExpanded ? 'Show less' : 'Show more'}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Build on Selected Ideas */}
            {selectedIdeas.length > 0 && (
              <div className="mb-4 flex gap-4 items-center">
                <button
                  className="btn-primary"
                  onClick={handleBuildOnSelected}
                  disabled={isGenerating}
                >
                  Build on Selected Ideas
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    setSelectedIdeas([])
                    setIdeaTexts({})
                  }}
                >
                  Clear Selection
                </button>
                <span className="text-gray-600 text-sm">
                  {selectedIdeas.length} idea(s) selected
                </span>
              </div>
            )}

            {/* Tabs */}
            <div className="border-b border-gray-300 mb-6">
              <div className="flex gap-2">
                {['hmw', 'features', 'sketches', 'context', 'layouts'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-6 py-3 font-medium transition-colors ${
                      activeTab === tab
                        ? 'text-primary border-b-2 border-primary'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {tab === 'hmw' && 'HMW Reframes'}
                    {tab === 'features' && 'Feature Ideas'}
                    {tab === 'sketches' && 'Concept Sketches'}
                    {tab === 'context' && 'User Context'}
                    {tab === 'layouts' && 'Layout Ideas'}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Content */}
            <div className="result-section">
              {activeTab === 'hmw' && (
                <HMWTab
                  hmwResults={hmwResults}
                  selectedIdeas={selectedIdeas}
                  ideaTexts={ideaTexts}
                  onToggleSelection={toggleIdeaSelection}
                />
              )}
              {activeTab === 'features' && (
                <FeaturesTab
                  featureIdeas={featureIdeas}
                  selectedIdeas={selectedIdeas}
                  ideaTexts={ideaTexts}
                  onToggleSelection={toggleIdeaSelection}
                />
              )}
              {activeTab === 'sketches' && (
                <SketchesTab
                  imageUrls={imageUrls}
                  sketchConcepts={sketchConcepts}
                  selectedIdeas={selectedIdeas}
                  ideaTexts={ideaTexts}
                  onToggleSelection={toggleIdeaSelection}
                />
              )}
              {activeTab === 'context' && (
                <ContextTab
                  userContext={userContext}
                  selectedIdeas={selectedIdeas}
                  ideaTexts={ideaTexts}
                  onToggleSelection={toggleIdeaSelection}
                />
              )}
              {activeTab === 'layouts' && (
                <LayoutsTab
                  layoutResults={layoutResults}
                  selectedIdeas={selectedIdeas}
                  ideaTexts={ideaTexts}
                  onToggleSelection={toggleIdeaSelection}
                />
              )}
            </div>
          </>
        )}

        {!hasResults && !isGenerating && (
          <div className="info-box">
            Enter a challenge above and click Generate to see results.
          </div>
        )}
        </div>
      </div>
    </div>
  )
}

// Tab Components
function HMWTab({ hmwResults, selectedIdeas, ideaTexts, onToggleSelection }) {
  if (!hmwResults || Object.keys(hmwResults).length === 0) {
    return <div className="info-box">No reframes generated yet.</div>
  }

  return (
    <div>
      <div className="result-heading">How Might We Statements:</div>
      {Object.entries(hmwResults).map(([themeName, statements], themeIdx) => {
        if (!statements || statements.length === 0) return null
        return (
          <div key={themeName}>
            {themeIdx > 0 && <div className="my-8 border-t border-gray-300"></div>}
            <h3 className="text-xl mt-8 mb-4 text-primary font-medium">{themeName}</h3>
            {statements.map((stmt, i) => {
              const ideaId = `hmw_${themeName}_${i}`
              const isSelected = selectedIdeas.includes(ideaId)
              return (
                <div 
                  key={i} 
                  className={`mb-4 cursor-pointer transition-all ${isSelected ? 'selected-idea' : 'hover:bg-gray-50 rounded p-2 -m-2'}`}
                  onClick={() => onToggleSelection(ideaId, stmt)}
                >
                  <div className="result-content">
                    <strong>{i + 1}.</strong> {stmt}
                  </div>
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

function FeaturesTab({ featureIdeas, selectedIdeas, ideaTexts, onToggleSelection }) {
  if (!featureIdeas || Object.keys(featureIdeas).length === 0) {
    return <div className="info-box">Feature ideas will appear here after generation.</div>
  }

  return (
    <div>
      <div className="result-heading">Feature Ideas:</div>
      {Object.entries(featureIdeas).map(([themeName, features], themeIdx) => {
        if (!features || features.length === 0) return null
        return (
          <div key={themeName}>
            {themeIdx > 0 && <div className="my-8 border-t border-gray-300"></div>}
            <h3 className="text-xl mt-8 mb-4 text-primary font-medium">{themeName}</h3>
            {features.map((featureData, i) => {
              const feature = typeof featureData === 'object' ? featureData.feature : featureData
              const rationale = typeof featureData === 'object' ? featureData.rationale : ''
              const ideaId = `feature_${themeName}_${i}`
              const ideaText = rationale ? `${feature}. ${rationale}` : feature
              const isSelected = selectedIdeas.includes(ideaId)
              return (
                <div 
                  key={i} 
                  className={`mb-4 cursor-pointer transition-all ${isSelected ? 'selected-idea' : 'hover:bg-gray-50 rounded p-2 -m-2'}`}
                  onClick={() => onToggleSelection(ideaId, ideaText)}
                >
                  <div className="result-content">
                    <strong>{i + 1}. {feature}</strong>
                  </div>
                  {rationale && (
                    <div className="mt-2 mb-4 text-gray-600 text-[0.9375rem] italic">
                      {rationale}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

function SketchesTab({ imageUrls, sketchConcepts, selectedIdeas, ideaTexts, onToggleSelection }) {
  if (!imageUrls || imageUrls.length === 0) {
    return <div className="info-box">Sketches will appear here after generation.</div>
  }

  return (
    <div>
      <div className="result-heading">Concept Sketches:</div>
      {imageUrls.map((url, i) => {
        if (!url) return null
        const conceptText = sketchConcepts[i] || ''
        const ideaId = `sketch_${i}`
        const isSelected = selectedIdeas.includes(ideaId)
        return (
          <div key={i}>
            {i > 0 && <div className="my-8 border-t border-gray-300"></div>}
            <div 
              className={`cursor-pointer transition-all ${isSelected ? 'selected-idea' : 'hover:bg-gray-50 rounded p-2 -m-2'}`}
              onClick={() => onToggleSelection(ideaId, conceptText)}
            >
              <img
                src={url}
                alt={`Sketch ${i + 1}`}
                className="rounded-lg shadow-md border border-gray-100 my-4 max-w-md"
              />
              {conceptText && (
                <p className="mt-3 mb-6 text-gray-600 text-[0.9375rem] leading-relaxed">
                  {conceptText}
                </p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ContextTab({ userContext, selectedIdeas, ideaTexts, onToggleSelection }) {
  if (!userContext || userContext.length === 0) {
    return <div className="info-box">User context will appear here after generation.</div>
  }

  return (
    <div>
      <div className="result-heading">User Context:</div>
      {userContext.map((segment, segmentIdx) => {
        const segmentName = segment.segment_name || `User Segment ${segmentIdx + 1}`
        const persona = segment.persona || {}
        const scenarios = segment.scenarios || []
        return (
          <div key={segmentIdx}>
            {segmentIdx > 0 && <div className="my-8 border-t border-gray-300"></div>}
            <h3 className="text-xl mt-8 mb-4 text-primary font-medium">{segmentName}</h3>
            
            {persona && persona.name && (
              <>
                <h4 className="text-lg mt-4 mb-2">Persona: {persona.name}</h4>
                {persona.description && (
                  <div 
                    className={`mb-4 cursor-pointer transition-all ${selectedIdeas.includes(`persona_${segmentIdx}`) ? 'selected-idea' : 'hover:bg-gray-50 rounded p-2 -m-2'}`}
                    onClick={() => {
                      const ideaId = `persona_${segmentIdx}`
                      const ideaText = `Persona: ${persona.name}. ${persona.description}`
                      onToggleSelection(ideaId, ideaText)
                    }}
                  >
                    <div className="result-content">
                      {persona.description}
                    </div>
                  </div>
                )}
              </>
            )}

            {scenarios.length > 0 && (
              <>
                <h4 className="text-lg mt-6 mb-2">Key Scenarios:</h4>
                {scenarios.map((scenario, i) => {
                  const ideaId = `scenario_${segmentIdx}_${i}`
                  const personaName = persona?.name || 'User'
                  const ideaText = `Persona: ${personaName}. Scenario: ${scenario}`
                  const isSelected = selectedIdeas.includes(ideaId)
                  return (
                    <div 
                      key={i} 
                      className={`mb-2 cursor-pointer transition-all ${isSelected ? 'selected-idea' : 'hover:bg-gray-50 rounded p-2 -m-2'}`}
                      onClick={() => onToggleSelection(ideaId, ideaText)}
                    >
                      <div className="result-content">
                        <strong>{i + 1}.</strong> {scenario}
                      </div>
                    </div>
                  )
                })}
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}

function LayoutsTab({ layoutResults, selectedIdeas, ideaTexts, onToggleSelection }) {
  if (!layoutResults || Object.keys(layoutResults).length === 0) {
    return <div className="info-box">Layout suggestions will appear here after generation.</div>
  }

  return (
    <div>
      <div className="result-heading">Layout Ideas:</div>
      {Object.entries(layoutResults).map(([themeName, layouts], themeIdx) => {
        if (!layouts || layouts.length === 0) return null
        return (
          <div key={themeName}>
            {themeIdx > 0 && <div className="my-8 border-t border-gray-300"></div>}
            <h3 className="text-xl mt-8 mb-4 text-primary font-medium">{themeName}</h3>
            {layouts.map((layout, i) => {
              const title = typeof layout === 'object' ? layout.title : `Layout ${i + 1}`
              const desc = typeof layout === 'object' ? layout.description : String(layout)
              const ideaId = `layout_${themeName}_${i}`
              const ideaText = `${title}: ${desc}`
              const isSelected = selectedIdeas.includes(ideaId)
              return (
                <div 
                  key={i} 
                  className={`mb-6 cursor-pointer transition-all ${isSelected ? 'selected-idea' : 'hover:bg-gray-50 rounded p-2 -m-2'}`}
                  onClick={() => onToggleSelection(ideaId, ideaText)}
                >
                  <h4 className="text-lg mt-6 mb-2">{i + 1}. {title}</h4>
                  <div className="result-content">{desc}</div>
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

export default App

