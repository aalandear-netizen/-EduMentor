/**
 * Typed API client for the EduMentor backend.
 */

const BASE = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? 'Request failed');
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Topic {
  id: string;
  label: string;
  description: string;
  prerequisites: string[];
  next: string[];
}

export interface SessionResponse {
  session_id: string;
  current_topic: string;
  level: string;
}

export interface ExplainResponse {
  topic_id: string;
  topic_label: string;
  explanation: string;
  level: string;
}

export interface QuestionResponse {
  topic_id: string;
  topic_label: string;
  difficulty: number;
  question: string;
  answer: string;
  explanation: string;
  hint: string | null;
}

export interface AnswerResponse {
  is_correct: boolean;
  feedback: string;
  recommendation: {
    difficulty: number;
    mastered: boolean;
    hint_recommended: boolean;
    action: string;
  };
  next_topic: string | null;
}

export interface ChatResponse {
  response: string;
  topic_id: string;
  level: string;
}

export interface DiagnosticAnswer {
  question: string;
  student_answer: string;
  correct_answer: string;
  is_correct: boolean;
}

export interface DiagnosticResponse {
  session_id: string;
  level: string;
  reasoning: string;
  suggested_topic: string;
}

export interface ProgressResponse {
  session_id: string;
  student_level: string;
  current_topic: string;
  mastered_topics: string[];
  topics: Record<string, {
    correct: number;
    incorrect: number;
    difficulty: number;
    mastered: boolean;
  }>;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const api = {
  /** Create a new tutoring session */
  createSession: (initial_topic?: string, initial_level?: string) =>
    request<SessionResponse>('/tutoring/session', {
      method: 'POST',
      body: JSON.stringify({ initial_topic, initial_level }),
    }),

  /** Get session progress */
  getProgress: (sessionId: string) =>
    request<ProgressResponse>(`/tutoring/session/${sessionId}/progress`),

  /** Get an explanation for a topic */
  explain: (session_id: string, topic_id: string) =>
    request<ExplainResponse>('/tutoring/explain', {
      method: 'POST',
      body: JSON.stringify({ session_id, topic_id }),
    }),

  /** Generate a practice question */
  generateQuestion: (session_id: string, topic_id: string) =>
    request<QuestionResponse>('/tutoring/question', {
      method: 'POST',
      body: JSON.stringify({ session_id, topic_id }),
    }),

  /** Submit an answer */
  submitAnswer: (
    session_id: string,
    topic_id: string,
    question: string,
    correct_answer: string,
    student_answer: string
  ) =>
    request<AnswerResponse>('/tutoring/answer', {
      method: 'POST',
      body: JSON.stringify({ session_id, topic_id, question, correct_answer, student_answer }),
    }),

  /** Send a chat message */
  chat: (session_id: string, topic_id: string, message: string, history: object[]) =>
    request<ChatResponse>('/tutoring/chat', {
      method: 'POST',
      body: JSON.stringify({ session_id, topic_id, message, history }),
    }),

  /** Submit diagnostic quiz */
  submitDiagnostic: (session_id: string, topic: string, answers: DiagnosticAnswer[]) =>
    request<DiagnosticResponse>('/tutoring/diagnostic', {
      method: 'POST',
      body: JSON.stringify({ session_id, topic, answers }),
    }),

  /** List all knowledge graph topics */
  listTopics: () =>
    request<{ topics: Topic[] }>('/kg/topics'),
};
