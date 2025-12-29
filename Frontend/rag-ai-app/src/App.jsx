import { useState } from 'react'
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState('IDLE') // IDLE, LOADING, READY, ERROR
  const [chatLog, setChatLog] = useState([])
  const [question, setQuestion] = useState('')

  // 1. Send Video to Backend
  const handleProcess = async () => {
    if (!url) return
    setStatus('LOADING')
    
    try {
      // Connects to your FastAPI (ensure api.py is running!)
      const response = await fetch('${API_BASE_URL}/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, name: "demo_video" })
      })
      
      const data = await response.json()
      if (data.status === 'success') {
        setStatus('READY')
        setChatLog(prev => [...prev, { role: 'sys', text: `>> SYSTEM: Analysis completed, You can ask your questions now` }])
      }
    } catch (error) {
      console.error(error)
      setStatus('ERROR')
      setChatLog(prev => [...prev, { role: 'sys', text: `>> ERROR: Connection failed.` }])
    }
  }

  // 2. Ask Question
  const handleAsk = async () => {
    if (!question) return
    const userQ = question
    setQuestion('')
    
    // Add user question to log
    setChatLog(prev => [...prev, { role: 'user', text: `> USER: ${userQ}` }])

    try {
      const response = await fetch('${API_BASE_URL}/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQ })
      })
      const data = await response.json()
      
      // Add AI answer to log
      setChatLog(prev => [...prev, { 
        role: 'ai', 
        text: `>> AI: ${data.answer}`, 
        sources: data.sources 
      }])
    } catch (error) {
      setChatLog(prev => [...prev, { role: 'sys', text: `>> ERROR: Failed to get answer.` }])
    }
  }

  return (
    <div className="min-h-screen bg-black text-green-500 p-8 font-mono selection:bg-green-900 selection:text-white">
      
      {/* --- HEADER --- */}
      <div className="max-w-4xl mx-auto border-b-2 border-green-700 pb-4 mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-bold tracking-tighter">RAG video model v-1</h1>
          <p className="text-xs text-green-800 mt-1">MADE BY ABHAV</p>
        </div>
        <div className={`text-sm ${status === 'LOADING' ? 'animate-pulse' : ''}`}>
          STATUS: <span className={status === 'READY' ? 'text-green-400' : 'text-red-500'}>[{status}]</span>
        </div>
      </div>

      {/* --- CONTROL PANEL --- */}
      <div className="max-w-4xl mx-auto mb-8 border border-green-900 p-4 bg-gray-900/50 rounded">
        <label className="text-xs text-green-700 mb-1 block">INPUT_SOURCE (YouTube URL)</label>
        <div className="flex gap-2">
          <input 
            type="text" 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            className="flex-1 bg-black border border-green-800 p-2 text-sm focus:outline-none focus:border-green-500 placeholder-green-900"
          />
          <button 
            onClick={handleProcess}
            disabled={status === 'LOADING'}
            className="bg-green-900 hover:bg-green-700 text-black font-bold px-6 text-sm border border-green-600 disabled:opacity-50"
          >
            {status === 'LOADING' ? 'INITIALIZING...' : 'EXECUTE'}
          </button>
        </div>
      </div>

      {/* --- TERMINAL OUTPUT (Chat) --- */}
      <div className="max-w-4xl mx-auto border border-green-800 bg-black min-h-[400px] p-4 mb-4 overflow-y-auto font-mono text-sm relative shadow-[0_0_20px_rgba(0,255,0,0.1)]">
        {chatLog.length === 0 && (
          <div className="text-green-900 text-center mt-20">
            [WAITING FOR INPUT...]<br/>
            [SYSTEM READY]
          </div>
        )}
        
        {chatLog.map((msg, idx) => (
          <div key={idx} className="mb-4">
            <span className={`font-bold ${msg.role === 'ai' ? 'text-green-400' : msg.role === 'sys' ? 'text-yellow-500' : 'text-blue-400'}`}>
              {msg.text.split(':')[0]}:
            </span>
            <span className="ml-2 text-gray-300">
              {msg.text.split(':').slice(1).join(':')}
            </span>
            
            {/* Show Timestamps if available */}
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-1 ml-4 text-xs text-green-800">
                Sources: {msg.sources.join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* --- COMMAND INPUT --- */}
      <div className="max-w-4xl mx-auto flex gap-2">
        <span className="text-green-500 py-2">{'>'}</span>
        <input 
          type="text" 
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
          placeholder="Enter query command..."
          className="flex-1 bg-transparent border-b border-green-800 p-2 text-green-400 focus:outline-none focus:border-green-500"
        />
      </div>

    </div>
  )
}

export default App