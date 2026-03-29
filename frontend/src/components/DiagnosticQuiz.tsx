import React from 'react';
import './DiagnosticQuiz.css';

interface Question {
  question: string;
  options: string[];
  correct: string;
}

const QUIZ_QUESTIONS: Question[] = [
  {
    question: 'What is 12 × 8?',
    options: ['86', '96', '106', '116'],
    correct: '96',
  },
  {
    question: 'Solve for x: 3x - 5 = 10',
    options: ['x = 3', 'x = 5', 'x = 7', 'x = 15'],
    correct: 'x = 5',
  },
  {
    question: 'What is the slope of y = 2x + 3?',
    options: ['3', '2', '5', '−2'],
    correct: '2',
  },
  {
    question: 'Expand: (x + 2)²',
    options: ['x² + 4', 'x² + 4x + 4', 'x² + 2x + 4', 'x² + 4x + 2'],
    correct: 'x² + 4x + 4',
  },
  {
    question: 'What is the derivative of x³?',
    options: ['x²', '3x', '3x²', '3x³'],
    correct: '3x²',
  },
];

interface Props {
  onComplete: (level: string, suggestedTopic: string) => void;
}

const DiagnosticQuiz: React.FC<Props> = ({ onComplete }) => {
  const [current, setCurrent] = React.useState(0);
  const [answers, setAnswers] = React.useState<string[]>([]);
  const [selected, setSelected] = React.useState<string | null>(null);
  const [submitted, setSubmitted] = React.useState(false);

  const q = QUIZ_QUESTIONS[current];

  const handleSelect = (opt: string) => {
    if (submitted) return;
    setSelected(opt);
  };

  const handleNext = () => {
    if (!selected) return;
    const newAnswers = [...answers, selected];
    setAnswers(newAnswers);

    if (current < QUIZ_QUESTIONS.length - 1) {
      setCurrent(current + 1);
      setSelected(null);
      setSubmitted(false);
    } else {
      // Evaluate
      const correct = newAnswers.filter((a, i) => a === QUIZ_QUESTIONS[i].correct).length;
      const pct = correct / QUIZ_QUESTIONS.length;
      let level = 'beginner';
      let topic = 'arithmetic';
      if (pct >= 0.8) {
        level = 'advanced';
        topic = 'calculus_limits';
      } else if (pct >= 0.5) {
        level = 'intermediate';
        topic = 'algebra_intermediate';
      }
      onComplete(level, topic);
    }
  };

  const progress = ((current) / QUIZ_QUESTIONS.length) * 100;

  return (
    <div className="quiz-container">
      <div className="quiz-header">
        <h2>📋 Diagnostic Quiz</h2>
        <p className="quiz-subtitle">Help us personalise your learning experience</p>
      </div>

      <div className="quiz-progress">
        <div className="quiz-progress-bar" style={{ width: `${progress}%` }} />
        <span className="quiz-progress-label">{current + 1} / {QUIZ_QUESTIONS.length}</span>
      </div>

      <div className="quiz-question">
        <p className="question-text">{q.question}</p>
        <div className="options">
          {q.options.map((opt) => (
            <button
              key={opt}
              className={`option-btn ${selected === opt ? 'selected' : ''}`}
              onClick={() => handleSelect(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>

      <button
        className="btn-primary next-btn"
        onClick={handleNext}
        disabled={!selected}
      >
        {current < QUIZ_QUESTIONS.length - 1 ? 'Next →' : 'See Results →'}
      </button>
    </div>
  );
};

export default DiagnosticQuiz;
