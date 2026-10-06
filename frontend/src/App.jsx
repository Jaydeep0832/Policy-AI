import React, { useState } from 'react';
import { API_BASE } from './apiConfig';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import FailoverView from './components/FailoverView';
import ExplainerView from './components/ExplainerView';
import PoliciesView from './components/PoliciesView';
import RAGInspectorDrawer from './components/RAGInspectorDrawer';

export default function App() {
  const [activeView, setActiveView] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [selectedDept, setSelectedDept] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectData, setInspectData] = useState(null);

  const handleSelectPreset = (question) => {
    setActiveView('chat');
    setInputQuestion(question);
    submitQuestion(question, selectedDept);
  };

  const submitQuestion = async (questionToAsk, dept) => {
    const q = questionToAsk.trim();
    if (!q) return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: q }]);
    setInputQuestion('');
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, department: dept || null })
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errorText}`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          userQuestion: q,
          response: data
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          userQuestion: q,
          response: {
            status: 'insufficient_information',
            answer: `An error occurred while evaluating the query: ${err.message}`,
            has_conflict: false,
            conflict_analysis: null,
            citations: [],
            retrieval_metrics: {
              e2e_latency_ms: 0,
              model_used: 'Error Fallback',
              is_grounded: false,
              groundedness_verdict: 'Request Failed to Execute'
            }
          }
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspect = (data) => {
    setInspectData(data);
    setInspectorOpen(true);
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <div className="app-container">
      <div className="ambient-glow"></div>

      {/* Left Sidebar */}
      <Sidebar
        activeView={activeView}
        setActiveView={setActiveView}
        onSelectPreset={handleSelectPreset}
      />

      {/* Main Canvas */}
      <div className="main-canvas">
        {/* Top Navbar */}
        <header className="top-navbar">
          <div className="scope-wrap">
            <span>Department Scope:</span>
            <select
              className="scope-select"
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
            >
              <option value="">All Institutional Cadres</option>
              <option value="Staff HR">Staff HR (General Cadre)</option>
              <option value="Executive">Executive Cadre (Addenda)</option>
              <option value="Academic">Academic & Faculty</option>
            </select>
          </div>

          <div className="top-actions">
            <button className="btn-secondary" onClick={handleClearChat}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
              <span>Clear Chat</span>
            </button>
            <a href="/docs" target="_blank" rel="noreferrer" className="btn-secondary">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
              <span>Swagger API</span>
            </a>
          </div>
        </header>

        {/* View Routing */}
        {activeView === 'chat' && (
          <ChatView
            messages={messages}
            inputQuestion={inputQuestion}
            setInputQuestion={setInputQuestion}
            selectedDept={selectedDept}
            setSelectedDept={setSelectedDept}
            isLoading={isLoading}
            onSubmit={() => submitQuestion(inputQuestion, selectedDept)}
            onInspect={handleInspect}
            onSelectPreset={handleSelectPreset}
          />
        )}

        {activeView === 'failover' && <FailoverView />}

        {activeView === 'explainer' && <ExplainerView />}

        {activeView === 'policies' && <PoliciesView />}
      </div>

      {/* RAG Groundedness Inspector Drawer */}
      <RAGInspectorDrawer
        isOpen={inspectorOpen}
        onClose={() => setInspectorOpen(false)}
        inspectData={inspectData}
      />
    </div>
  );
}
