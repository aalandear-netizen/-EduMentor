import React from 'react';
import './App.css';
import DiagnosticQuiz from './components/DiagnosticQuiz';
import ChatInterface from './components/ChatInterface';
import ProgressDashboard from './components/ProgressDashboard';
import { api, ProgressResponse, Topic } from './services/api';

type AppPhase = 'loading' | 'diagnostic' | 'tutoring' | 'error';

const App: React.FC = () => {
  const [phase, setPhase] = React.useState<AppPhase>('diagnostic');
  const [error, setError] = React.useState<string | null>(null);

  const [sessionId, setSessionId] = React.useState<string>('');
  const [currentTopicId, setCurrentTopicId] = React.useState<string>('arithmetic');
  const [level, setLevel] = React.useState<string>('beginner');
  const [topics, setTopics] = React.useState<Topic[]>([]);
  const [progress, setProgress] = React.useState<ProgressResponse | null>(null);

  // Load topic list on mount
  React.useEffect(() => {
    api.listTopics()
      .then(({ topics: t }) => setTopics(t))
      .catch(() => {/* non-fatal – topics will be empty */});
  }, []);

  // Refresh progress whenever topic or session changes
  React.useEffect(() => {
    if (!sessionId) return;
    api.getProgress(sessionId)
      .then(setProgress)
      .catch(() => {/* best-effort */});
  }, [sessionId, currentTopicId]);

  const handleDiagnosticComplete = async (detectedLevel: string, suggestedTopic: string) => {
    setPhase('loading');
    try {
      const session = await api.createSession(suggestedTopic, detectedLevel);
      setSessionId(session.session_id);
      setCurrentTopicId(session.current_topic);
      setLevel(detectedLevel);
      setPhase('tutoring');
    } catch (e) {
      setError((e as Error).message);
      setPhase('error');
    }
  };

  const handleTopicChange = async (topicId: string) => {
    setCurrentTopicId(topicId);
    if (sessionId) {
      try {
        const p = await api.getProgress(sessionId);
        setProgress(p);
      } catch {/* ignore */}
    }
  };

  const currentTopic = topics.find((t) => t.id === currentTopicId);

  if (phase === 'loading') {
    return (
      <div className="app-center">
        <div className="spinner" />
        <p>Setting up your personalised session…</p>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className="app-center">
        <h2>⚠️ Something went wrong</h2>
        <p>{error}</p>
        <button className="btn-primary" onClick={() => { setError(null); setPhase('diagnostic'); }}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <span className="logo">🎓</span>
          <span className="brand-name">EduMentor</span>
          <span className="brand-tagline">AI Adaptive Tutor</span>
        </div>
        {phase === 'tutoring' && (
          <button
            className="btn-restart"
            onClick={() => { setPhase('diagnostic'); setSessionId(''); setProgress(null); }}
          >
            Restart
          </button>
        )}
      </header>

      {/* Main content */}
      <main className="app-main">
        {phase === 'diagnostic' && (
          <div className="diagnostic-wrapper">
            <DiagnosticQuiz onComplete={handleDiagnosticComplete} />
          </div>
        )}

        {phase === 'tutoring' && sessionId && (
          <div className="tutoring-layout">
            {/* Left: progress sidebar */}
            <aside className="sidebar">
              {progress && (
                <ProgressDashboard
                  progress={progress}
                  topics={topics}
                  currentTopicId={currentTopicId}
                  onSelectTopic={handleTopicChange}
                />
              )}
              {!progress && topics.length > 0 && (
                <div className="sidebar-placeholder">
                  <p>📊 Progress will appear here once you start answering questions.</p>
                </div>
              )}
            </aside>

            {/* Right: chat */}
            <section className="chat-section">
              <ChatInterface
                sessionId={sessionId}
                topicId={currentTopicId}
                topicLabel={currentTopic?.label ?? currentTopicId}
                level={level}
                onTopicChange={handleTopicChange}
              />
            </section>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
