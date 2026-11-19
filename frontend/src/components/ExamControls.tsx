import { useEffect, useState } from 'react';
import { BookOpen, SlidersHorizontal } from 'lucide-react';
import { fetchChapters } from '../api/ragClient';

interface ExamControlsProps {
  chapter: string;
  setChapter: (val: string) => void;
  questionType: 'objective' | 'subjective';
  setQuestionType: (val: 'objective' | 'subjective') => void;
  marks: number;
  setMarks: (val: number) => void;
}

export function ExamControls({
  chapter,
  setChapter,
  questionType,
  setQuestionType,
  marks,
  setMarks,
}: ExamControlsProps) {
  const [chapters, setChapters] = useState<string[]>([]);

  useEffect(() => {
    fetchChapters()
      .then(setChapters)
      .catch((err) => console.error('Could not load chapters:', err));
  }, []);

  const handleTypeChange = (type: 'objective' | 'subjective') => {
    setQuestionType(type);
    if (type === 'objective') setMarks(1);
    else if (marks === 1) setMarks(3);
  };

  return (
    <div className="bg-white border-b border-slate-200 px-4 py-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Dynamic Chapter Selector */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <BookOpen className="w-4 h-4 text-indigo-600 shrink-0" />
          <select
            value={chapter}
            onChange={(e) => setChapter(e.target.value)}
            className="w-full sm:w-64 rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700 focus:border-indigo-500 focus:outline-none"
          >
            <option value="">All Textbook Chapters ({chapters.length})</option>
            {chapters.map((fileName) => (
              <option key={fileName} value={fileName}>
                {fileName}
              </option>
            ))}
          </select>
        </div>

        {/* Question Type & Marks Pills */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex rounded-lg bg-slate-100 p-1">
            {(['subjective', 'objective'] as const).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => handleTypeChange(type)}
                className={`px-3 py-1 rounded-md text-xs font-semibold capitalize transition ${
                  questionType === type
                    ? 'bg-white text-indigo-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400 mr-1" />
            {[1, 2, 3, 5].map((m) => (
              <button
                key={m}
                type="button"
                disabled={questionType === 'objective' && m !== 1}
                onClick={() => setMarks(m)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold border transition ${
                  marks === m
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-40'
                }`}
              >
                {m}M
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
