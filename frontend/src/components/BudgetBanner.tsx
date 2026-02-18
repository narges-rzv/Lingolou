import { useState, useEffect } from 'react';
import { publicApiFetch } from '../api';
import type { BudgetStatus } from '../types';

export default function BudgetBanner() {
  const [budget, setBudget] = useState<BudgetStatus | null>(null);

  useEffect(() => {
    publicApiFetch('/public/budget')
      .then(setBudget)
      .catch(() => {});
  }, []);

  if (!budget) return null;

  const pct = Math.min((budget.total_spent / budget.total_budget) * 100, 100);
  const exhausted = budget.total_spent >= budget.total_budget;

  return (
    <div className={`budget-banner ${exhausted ? 'budget-banner-exhausted' : ''}`}>
      <div className="budget-banner-text">
        {exhausted ? (
          <span>Community pool used up — add your own API keys to continue</span>
        ) : (
          <span>
            Community pool: ${budget.total_spent.toFixed(2)} / ${budget.total_budget.toFixed(2)} used
            {' \u00b7 '}
            {budget.free_stories_generated} free {budget.free_stories_generated === 1 ? 'story' : 'stories'} generated
          </span>
        )}
      </div>
      <div className="budget-progress">
        <div className="budget-progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
