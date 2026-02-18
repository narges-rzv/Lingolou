import { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../api';
import { TaskStatusResponse } from '../types';

interface TaskProgressProps {
  taskId: string | null;
  onComplete?: (result: Record<string, unknown>) => void;
  onError?: (msg: string) => void;
}

export default function TaskProgress({ taskId, onComplete, onError }: TaskProgressProps) {
  const [status, setStatus] = useState<TaskStatusResponse | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const data: TaskStatusResponse = await apiFetch(`/stories/tasks/${taskId}`);
        setStatus(data);
        setPollCount((c) => c + 1);

        if (data.status === 'completed') {
          clearInterval(intervalRef.current!);
          // Check if the task "completed" but the result indicates failure
          const result = data.result as Record<string, unknown> | null;
          if (result?.status === 'failed') {
            onError?.((result.error as string) || 'Task failed');
          } else {
            onComplete?.(result ?? {});
          }
        } else if (data.status === 'failed') {
          clearInterval(intervalRef.current!);
          onError?.(data.message ?? 'Task failed');
        }
      } catch (err) {
        clearInterval(intervalRef.current!);
        onError?.((err as Error).message);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId]);

  const handleCancel = async () => {
    try {
      await apiFetch(`/stories/tasks/${taskId}`, { method: 'DELETE' });
      if (intervalRef.current) clearInterval(intervalRef.current);
      onError?.('Task cancelled');
    } catch {
      // ignore cancel errors
    }
  };

  if (!status) return null;

  const isPending = status.status === 'pending';
  const isDone = status.status === 'completed' || status.status === 'failed';

  return (
    <div className="task-progress">
      <div className="task-progress-header">
        <span className="task-progress-message">
          {status.message}
        </span>
        <span className="progress-percent">{Math.round(status.progress || 0)}%</span>
      </div>
      <div className="progress-bar-track">
        <div
          className={`progress-bar-fill ${isPending ? 'progress-bar-pending' : ''}`}
          style={{ width: `${status.progress || (isPending ? 100 : 0)}%` }}
        />
      </div>
      {status.words_generated != null && status.estimated_total_words != null && (
        <div className="task-word-count" style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
          ~{status.words_generated.toLocaleString()} / {status.estimated_total_words.toLocaleString()} words
        </div>
      )}
      <div className="task-progress-footer">
        <span className="task-debug">
          Status: {status.status}
          {isPending && pollCount > 2 && ' — waiting for background task to start'}
          {isPending && pollCount > 5 && '. Check server logs for errors.'}
        </span>
        {!isDone && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleCancel}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
