import React from 'react';
import './ChatInterface.css';
import { api, QuestionResponse } from '../services/api';

interface Message {
  role: 'user' | 'ai' | 'system';
  content: string;
  extra?: React.ReactNode;
}

interface ActiveQuestion {
  data: QuestionResponse;
  showAnswer: boolean;
  showHint: boolean;
}

interface Props {
  sessionId: string;
  topicId: string;
  topicLabel: string;
  level: string;
  onTopicChange?: (topicId: string) => void;
}

const ChatInterface: React.FC<Props> = ({
  sessionId, topicId, topicLabel, level, onTopicChange,
}) => {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [activeQuestion, setActiveQuestion] = React.useState<ActiveQuestion | null>(null);
  const [studentAnswer, setStudentAnswer] = React.useState('');
  const endRef = React.useRef<HTMLDivElement>(null);

  // Chat history for context (role/content pairs)
  const historyRef = React.useRef<{ role: string; content: string }[]>([]);

  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (msg: Message) => setMessages((prev) => [...prev, msg]);

  const handleExplain = async () => {
    setLoading(true);
    addMessage({ role: 'system', content: `📖 Getting explanation for "${topicLabel}"…` });
    try {
      const res = await api.explain(sessionId, topicId);
      addMessage({ role: 'ai', content: res.explanation });
      historyRef.current.push({ role: 'assistant', content: res.explanation });
    } catch (e) {
      addMessage({ role: 'system', content: `Error: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateQuestion = async () => {
    setLoading(true);
    addMessage({ role: 'system', content: '🧩 Generating a practice question…' });
    try {
      const q = await api.generateQuestion(sessionId, topicId);
      setActiveQuestion({ data: q, showAnswer: false, showHint: false });
      addMessage({ role: 'ai', content: `**Practice Question (difficulty ${q.difficulty}/5):**\n\n${q.question}` });
    } catch (e) {
      addMessage({ role: 'system', content: `Error: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!activeQuestion || !studentAnswer.trim()) return;
    setLoading(true);
    const { data: q } = activeQuestion;
    addMessage({ role: 'user', content: `My answer: ${studentAnswer}` });
    try {
      const res = await api.submitAnswer(sessionId, topicId, q.question, q.answer, studentAnswer);
      const icon = res.is_correct ? '✅' : '❌';
      addMessage({ role: 'ai', content: `${icon} ${res.feedback}` });
      if (!res.is_correct) {
        setActiveQuestion((prev) => prev ? { ...prev, showAnswer: false } : null);
      } else {
        setActiveQuestion(null);
      }
      if (res.next_topic && onTopicChange) {
        addMessage({
          role: 'system',
          content: `🎉 You've mastered "${topicLabel}"! Moving to the next topic…`,
        });
        onTopicChange(res.next_topic);
      }
    } catch (e) {
      addMessage({ role: 'system', content: `Error: ${(e as Error).message}` });
    } finally {
      setStudentAnswer('');
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput('');
    addMessage({ role: 'user', content: userMsg });
    historyRef.current.push({ role: 'user', content: userMsg });
    setLoading(true);
    try {
      const res = await api.chat(sessionId, topicId, userMsg, historyRef.current.slice(-10));
      addMessage({ role: 'ai', content: res.response });
      historyRef.current.push({ role: 'assistant', content: res.response });
    } catch (e) {
      addMessage({ role: 'system', content: `Error: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const renderMarkdown = (text: string) => {
    // Very simple markdown: bold (**text**), newlines
    return text.split('\n').map((line, i) => {
      const parts = line.split(/\*\*(.*?)\*\*/g);
      return (
        <React.Fragment key={i}>
          {parts.map((part, j) =>
            j % 2 === 1 ? <strong key={j}>{part}</strong> : part
          )}
          {i < text.split('\n').length - 1 && <br />}
        </React.Fragment>
      );
    });
  };

  return (
    <div className="chat-wrapper">
      <div className="chat-topic-bar">
        <span className="topic-badge">📚 {topicLabel}</span>
        <span className="level-badge">{level}</span>
      </div>

      <div className="messages-pane">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>👋 Welcome! Use the buttons below to start learning.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            {msg.role === 'ai' && <span className="avatar">🤖</span>}
            {msg.role === 'user' && <span className="avatar">🧑</span>}
            {msg.role === 'system' && <span className="avatar">ℹ️</span>}
            <div className="bubble">{renderMarkdown(msg.content)}</div>
          </div>
        ))}
        {loading && (
          <div className="message message-ai">
            <span className="avatar">🤖</span>
            <div className="bubble loading-bubble">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Active question answer box */}
      {activeQuestion && (
        <div className="answer-box">
          <input
            value={studentAnswer}
            onChange={(e) => setStudentAnswer(e.target.value)}
            placeholder="Type your answer…"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmitAnswer()}
            disabled={loading}
          />
          <div className="answer-actions">
            <button
              className="btn-submit"
              onClick={handleSubmitAnswer}
              disabled={loading || !studentAnswer.trim()}
            >
              Submit
            </button>
            {activeQuestion.data.hint && !activeQuestion.showHint && (
              <button
                className="btn-hint"
                onClick={() => {
                  setActiveQuestion((prev) => prev ? { ...prev, showHint: true } : null);
                  addMessage({ role: 'system', content: `💡 Hint: ${activeQuestion.data.hint}` });
                }}
              >
                Show Hint
              </button>
            )}
            <button
              className="btn-show-answer"
              onClick={() => {
                addMessage({
                  role: 'system',
                  content: `📖 Answer: ${activeQuestion.data.answer}\n\n${activeQuestion.data.explanation}`,
                });
                setActiveQuestion(null);
              }}
            >
              Show Answer
            </button>
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="action-bar">
        <button className="btn-action" onClick={handleExplain} disabled={loading}>
          📖 Explain Topic
        </button>
        <button className="btn-action" onClick={handleGenerateQuestion} disabled={loading}>
          🧩 Practice Question
        </button>
        <div className="chat-input-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the tutor anything…"
            onKeyDown={(e) => e.key === 'Enter' && handleChat()}
            disabled={loading}
          />
          <button className="btn-send" onClick={handleChat} disabled={loading || !input.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
