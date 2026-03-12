import { useState, useEffect, useRef, useCallback } from 'react';
import { apiFetch } from '../api';
import { TaskStatusResponse } from '../types';

const TASK_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

interface TaskProgressProps {
  taskId: string | null;
  onComplete?: (result: Record<string, unknown>) => void;
  onError?: (msg: string) => void;
}

export default function TaskProgress({ taskId, onComplete, onError }: TaskProgressProps) {
  const [status, setStatus] = useState<TaskStatusResponse | null>(null);
  const [pollCount, setPollCount] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;

  const cleanup = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const data: TaskStatusResponse = await apiFetch(`/stories/tasks/${taskId}`);
        setStatus(data);
        setPollCount((c) => c + 1);

        if (data.status === 'completed') {
          cleanup();
          const result = data.result as Record<string, unknown> | null;
          if (result?.status === 'failed') {
            onErrorRef.current?.((result.error as string) || 'Task failed');
          } else {
            onCompleteRef.current?.(result ?? {});
          }
        } else if (data.status === 'failed') {
          cleanup();
          onErrorRef.current?.(data.message ?? 'Task failed');
        }
      } catch (err) {
        cleanup();
        onErrorRef.current?.((err as Error).message);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);

    timeoutRef.current = setTimeout(() => {
      cleanup();
      onErrorRef.current?.('Task timed out after 15 minutes');
    }, TASK_TIMEOUT_MS);

    return cleanup;
  }, [taskId, cleanup]);

  const handleCancel = async () => {
    try {
      await apiFetch(`/stories/tasks/${taskId}`, { method: 'DELETE' });
      cleanup();
      onErrorRef.current?.('Task cancelled');
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
