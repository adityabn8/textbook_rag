export interface QueryRequest {
  question: string;
  marks: number;
  question_type: 'objective' | 'subjective';
  chapter: string | null;
}

export interface SourceChunk {
  file_name: string;
  score: number;
  text_preview: string;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: SourceChunk[];
}

export async function askTextbook(payload: QueryRequest): Promise<QueryResponse> {
  const response = await fetch('/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error (${response.status})`);
  }

  return response.json();
}

export async function fetchChapters(): Promise<string[]> {
  const response = await fetch('/api/v1/chapters');
  if (!response.ok) {
    throw new Error(`Failed to load chapters (${response.status})`);
  }
  const data = await response.json();
  return data.chapters ?? [];
}
