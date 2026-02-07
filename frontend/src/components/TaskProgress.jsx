import { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../api';

export default function TaskProgress({ taskId, onComplete, onError }) {
  const [status, setStatus] = useState(null);
  const [pollCount, setPollCount] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const data = await apiFetch(`/stories/tasks/${taskId}`);
        setStatus(data);
        setPollCount((c) => c + 1);

        if (data.status === 'completed') {
          clearInterval(intervalRef.current);
          // Check if the task "completed" but the result indicates failure
          if (data.result?.status === 'failed') {
            onError?.(data.result.error || 'Task failed');
          } else {
            onComplete?.(data.result);
          }
        } else if (data.status === 'failed') {
          clearInterval(intervalRef.current);
          onError?.(data.message);
        }
      } catch (err) {
        clearInterval(intervalRef.current);
        onError?.(err.message);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => clearInterval(intervalRef.current);
  }, [taskId]);

  const handleCancel = async () => {
    try {
      await apiFetch(`/stories/tasks/${taskId}`, { method: 'DELETE' });
      clearInterval(intervalRef.current);
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
      <div className="task-progress-footer">
        <span className="task-debug">
          Status: {status.status}
          {isPending && pollCount > 2 && ' — waiting for Celery worker to pick up task'}
          {isPending && pollCount > 5 && '. Check worker terminal for errors.'}
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
