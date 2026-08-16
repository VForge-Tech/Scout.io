import { useState } from 'react';
import { api } from '../lib/api';

interface FeedbackWidgetProps {
  context: string;
  chatbotId?: string;
  sourceId?: string;
  prompt?: string;
}

export default function FeedbackWidget({
  context,
  chatbotId,
  sourceId,
  prompt,
}: FeedbackWidgetProps) {
  const [rating, setRating] = useState<'up' | 'down' | null>(null);
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    setError('');
    try {
      await api.post('/analytics/feedback', {
        rating,
        message: message.trim() || null,
        context,
        chatbot_id: chatbotId || null,
        source_id: sourceId || null,
      });
      setSubmitted(true);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (submitted) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3">
        <p className="text-sm text-green-800">Thanks for the feedback!</p>
      </div>
    );
  }

  const buttonClass = (active: boolean) =>
    `px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
      active
        ? 'bg-blue-600 text-white border-blue-600'
        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
    }`;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
      <p className="text-sm text-gray-700 mb-3">
        {prompt || 'How was your experience?'}
      </p>
      <div className="flex items-center gap-3 mb-3">
        <button onClick={() => setRating('up')} className={buttonClass(rating === 'up')}>
          👍 Looks good
        </button>
        <button onClick={() => setRating('down')} className={buttonClass(rating === 'down')}>
          👎 Needs work
        </button>
      </div>
      {rating === 'down' && (
        <div className="mb-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={2}
            placeholder="What went wrong? (optional)"
            className="w-full border rounded-md px-3 py-2 text-sm"
          />
        </div>
      )}
      <button
        onClick={submit}
        disabled={!rating}
        className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm disabled:opacity-50"
      >
        Send feedback
      </button>
      {error && <div className="text-red-500 text-sm mt-2">{error}</div>}
    </div>
  );
}