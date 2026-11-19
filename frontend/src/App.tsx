import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { GraduationCap, Send, Loader2, HelpCircle, ListChecks, Lightbulb } from 'lucide-react';
import { askTextbook, type QueryResponse } from './api/ragClient';
import { ExamControls } from './components/ExamControls';
import { SourcesDrawer } from './components/SourcesDrawer';

const STARTER_QUESTIONS = [
  "Explain the reasons for Rajvir's excitement on seeing the tea plantation.",
  "Why did Lencho write a letter to God and what was the postmaster's reaction?",
  "What does courage mean to Nelson Mandela according to the chapter?",
];

export default function App() {
  const [question, setQuestion] = useState('');
  const [chapter, setChapter] = useState('');
  const [questionType, setQuestionType] = useState<'objective' | 'subjective'>('subjective');
  const [marks, setMarks] = useState<number>(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);

  const handleSubmit = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || loading) return;

    setQuestion(trimmed);
    setLoading(true);
    setError(null);

    try {
      const data = await askTextbook({
        question: trimmed,
        marks,
        question_type: questionType,
        chapter: chapter || null,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch answer.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 text-slate-900">
      {/* Header */}
      <header className="bg-indigo-950 text-white px-4 py-3.5 sm:px-6 shadow-xs">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <GraduationCap className="w-6 h-6 text-indigo-300" />
            <div>
              <h1 className="text-base sm:text-lg font-bold tracking-tight">
                NCERT Exam Study Desk
              </h1>
              <p className="text-xs text-indigo-300 hidden sm:block">
                Grounded Hybrid RAG • Qdrant + Gemini
              </p>
            </div>
          </div>
          <span className="text-xs bg-indigo-900/80 border border-indigo-700 px-2.5 py-1 rounded-full text-indigo-200">
            {marks}M {questionType}
          </span>
        </div>
      </header>

      {/* Top Exam Filter & Marks Controls */}
      <ExamControls
        chapter={chapter}
        setChapter={setChapter}
        questionType={questionType}
        setQuestionType={setQuestionType}
        marks={marks}
        setMarks={setMarks}
      />

      {/* Split Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto flex flex-col lg:flex-row">
        {/* Left: Question & Grounded Answer Workspace */}
        <section className="flex-1 p-4 sm:p-6 flex flex-col gap-5">
          {/* Question Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(question);
            }}
            className="bg-white rounded-2xl p-3 sm:p-4 shadow-xs border border-slate-200"
          >
            <textarea
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(question);
                }
              }}
              placeholder="Type or paste an exam question from your textbook..."
              className="w-full resize-none border-0 bg-transparent text-sm sm:text-base text-slate-800 placeholder:text-slate-400 focus:outline-none"
            />
            <div className="flex items-center justify-between pt-2 border-t border-slate-100 mt-2">
              <span className="text-xs text-slate-400">
                Press Enter to ask • Shift + Enter for new line
              </span>
              <button
                type="submit"
                disabled={loading || question.trim().length < 3}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 transition cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Get Exam Answer
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Error Banner */}
          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 p-4 text-sm text-red-700">
              <strong>Error:</strong> {error}. Make sure your FastAPI server is running on port 8000.
            </div>
          )}

          {/* Answer Display Card OR Starter Prompts */}
          {loading ? (
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-3">
              <div className="h-4 w-1/3 bg-slate-200 rounded animate-pulse" />
              <div className="h-4 w-full bg-slate-100 rounded animate-pulse" />
              <div className="h-4 w-5/6 bg-slate-100 rounded animate-pulse" />
              <div className="h-4 w-4/6 bg-slate-100 rounded animate-pulse" />
            </div>
          ) : result ? (
            <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-xs space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <span className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                  {marks}-Mark {questionType} Response
                </span>
                <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-1">
                  {result.question}
                </h2>
              </div>

              <div className="prose prose-slate prose-sm sm:prose-base max-w-none leading-relaxed text-slate-700 space-y-2">
                <ReactMarkdown>{result.answer}</ReactMarkdown>
              </div>

              {/* One-Click Study Action Chips */}
              <div className="pt-4 border-t border-slate-100 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleSubmit(`Simplify this explanation in easy words: ${result.question}`)}
                  className="inline-flex items-center gap-1.5 text-xs font-medium bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 px-3 py-1.5 rounded-lg transition"
                >
                  <Lightbulb className="w-3.5 h-3.5" />
                  Simplify explanation
                </button>
                <button
                  type="button"
                  onClick={() => handleSubmit(`Create 3 practice MCQs with answers based on: ${result.question}`)}
                  className="inline-flex items-center gap-1.5 text-xs font-medium bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-700 px-3 py-1.5 rounded-lg transition"
                >
                  <ListChecks className="w-3.5 h-3.5" />
                  Turn into 3 MCQs
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-xs">
              <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2 mb-3">
                <HelpCircle className="w-4 h-4 text-indigo-600" />
                Try a Sample Board Exam Question
              </h3>
              <div className="grid gap-2.5">
                {STARTER_QUESTIONS.map((sample, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSubmit(sample)}
                    className="text-left text-sm p-3 rounded-xl border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 text-slate-700 transition"
                  >
                    {sample}
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Right: Retrieved Textbook Citations */}
        <SourcesDrawer sources={result?.sources ?? []} loading={loading} />
      </main>
    </div>
  );
}