import React from 'react';
import './ProgressDashboard.css';
import { ProgressResponse, Topic } from '../services/api';

interface Props {
  progress: ProgressResponse;
  topics: Topic[];
  currentTopicId: string;
  onSelectTopic: (topicId: string) => void;
}

const DIFFICULTY_LABELS: Record<number, string> = {
  1: 'Very Easy', 2: 'Easy', 3: 'Medium', 4: 'Hard', 5: 'Advanced',
};

const ProgressDashboard: React.FC<Props> = ({ progress, topics, currentTopicId, onSelectTopic }) => {
  const topicMap = Object.fromEntries(topics.map((t) => [t.id, t]));

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h3>📊 Your Progress</h3>
        <div className={`level-chip level-chip--${progress.student_level}`}>
          Level: <strong>{progress.student_level}</strong>
        </div>
      </div>

      <div className="topic-list">
        {topics.map((topic) => {
          const ts = progress.topics[topic.id];
          const isCurrent = topic.id === currentTopicId;
          const isMastered = progress.mastered_topics.includes(topic.id);
          const isLocked = topic.prerequisites.some(
            (p) => !progress.mastered_topics.includes(p) && topics.some((t) => t.id === p)
          );

          return (
            <button
              key={topic.id}
              className={`topic-card ${isCurrent ? 'current' : ''} ${isMastered ? 'mastered' : ''} ${isLocked ? 'locked' : ''}`}
              onClick={() => !isLocked && onSelectTopic(topic.id)}
              disabled={isLocked}
              title={isLocked ? `Complete prerequisites first: ${topic.prerequisites.join(', ')}` : ''}
            >
              <div className="topic-card-header">
                <span className="topic-icon">
                  {isMastered ? '✅' : isCurrent ? '📍' : isLocked ? '🔒' : '○'}
                </span>
                <span className="topic-name">{topic.label}</span>
              </div>
              {ts && (
                <div className="topic-stats">
                  <span className="stat">✓ {ts.correct}</span>
                  <span className="stat">✗ {ts.incorrect}</span>
                  <span className="stat">Diff: {DIFFICULTY_LABELS[ts.difficulty] ?? ts.difficulty}</span>
                </div>
              )}
              {!ts && !isLocked && (
                <div className="topic-stats">
                  <span className="stat not-started">Not started</span>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {progress.mastered_topics.length > 0 && (
        <div className="mastery-summary">
          🎓 Mastered {progress.mastered_topics.length} / {topics.length} topics
        </div>
      )}
    </div>
  );
};

export default ProgressDashboard;
