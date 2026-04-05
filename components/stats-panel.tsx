"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { State } from "@/lib/api";

interface StatsPanelProps {
  state: State | null;
  isLoading?: boolean;
}

export function StatsPanel({ state, isLoading }: StatsPanelProps) {
  const getAccuracy = () => {
    if (!state) return 0;

    // Extract total and processed from progress string (e.g., "2/5")
    const progressParts = state.progress?.split('/') || [];
    const processed = parseInt(progressParts[0]) || 0;
    const total = parseInt(progressParts[1]) || 1;

    if (total === 0) return 0;

    // Use correct_action_count if available, otherwise use processed count
    const correct = state.correct_action_count !== undefined
      ? state.correct_action_count
      : processed;

    return Math.round((correct / total) * 100);
  };

  const normalizedScore = state?.normalized_score !== undefined
    ? Math.min(1, Math.max(0, state.normalized_score))
    : 0;

  return (
    <div className="grid gap-3 grid-cols-2 sm:grid-cols-3">
      <Card className="border-border/30 bg-card/40 backdrop-blur">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Progress
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">
            {state?.progress || "0/0"}
          </div>
          <p className="text-xs text-muted-foreground mt-1">emails processed</p>
        </CardContent>
      </Card>

      <Card className="border-border/30 bg-card/40 backdrop-blur">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Accuracy
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">
            {getAccuracy()}%
          </div>
          <p className="text-xs text-muted-foreground mt-1">correct actions</p>
        </CardContent>
      </Card>

      <Card className="border-border/30 bg-card/40 backdrop-blur">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-foreground">
            {(normalizedScore * 10).toFixed(1)}/10
          </div>
          <p className="text-xs text-muted-foreground mt-1">quality score</p>
        </CardContent>
      </Card>
    </div>
  );
}
