"use client";

import { Reward, GradeResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface FeedbackPanelProps {
  reward: Reward | null;
  gradeResult: GradeResponse | null;
  isLoading?: boolean;
  isDone?: boolean;
}

export function FeedbackPanel({
  reward,
  gradeResult,
  isLoading,
  isDone,
}: FeedbackPanelProps) {
  if (isDone && gradeResult) {
    const isExcellent = gradeResult.score >= 0.8;
    const isGood = gradeResult.score >= 0.6 && gradeResult.score < 0.8;
    const isPoor = gradeResult.score < 0.6;

    return (
      <Card className="border-border/30 bg-gradient-to-br from-accent/20 to-card/40 backdrop-blur">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Task Complete! 🎉</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Final Score
              </span>
              <Badge
                className={cn(
                  isExcellent
                    ? "bg-green-500/30 text-green-700 dark:text-green-400"
                    : isGood
                      ? "bg-blue-500/30 text-blue-700 dark:text-blue-400"
                      : "bg-orange-500/30 text-orange-700 dark:text-orange-400"
                )}
              >
                {(gradeResult.score * 10).toFixed(1)}/10
              </Badge>
            </div>

            <p className="text-sm text-foreground/80">{gradeResult.message}</p>
          </div>

          {gradeResult.correct_actions !== undefined && (
            <div className="space-y-2 pt-2 border-t border-border/20">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Correct Actions</span>
                <span className="font-semibold text-foreground">
                  {gradeResult.correct_actions}/{gradeResult.total_actions}
                </span>
              </div>
            </div>
          )}

          <div className="pt-2 text-xs text-muted-foreground">
            {isExcellent && "🏆 Excellent performance!"}
            {isGood && "👍 Good job!"}
            {isPoor && "💪 Keep practicing!"}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="border-border/30 bg-card/40 backdrop-blur">
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-2">
            <div className="h-2 w-2 rounded-full bg-muted animate-bounce" />
            <div
              className="h-2 w-2 rounded-full bg-muted animate-bounce"
              style={{ animationDelay: "0.1s" }}
            />
            <div
              className="h-2 w-2 rounded-full bg-muted animate-bounce"
              style={{ animationDelay: "0.2s" }}
            />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!reward) {
    return (
      <Card className="border-border/30 bg-card/40 backdrop-blur">
        <CardContent className="pt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Select a task and take an action
          </p>
        </CardContent>
      </Card>
    );
  }

  const isCorrect = reward.score === 1.0;

  return (
    <Card
      className={cn(
        "border-border/30 backdrop-blur transition-all duration-300",
        isCorrect
          ? "bg-green-500/10 border-green-500/20"
          : "bg-red-500/10 border-red-500/20"
      )}
    >
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          {isCorrect ? "✓ Correct!" : "✗ Incorrect"}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        <p className="text-sm text-foreground/80">{reward.reason}</p>

        <div className="space-y-1 pt-2 border-t border-border/20 text-xs text-muted-foreground">
          <div className="flex justify-between">
            <span>Step Reward</span>
            <span className="font-semibold text-foreground">
              +{reward.score.toFixed(1)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Cumulative</span>
            <span className="font-semibold text-foreground">
              {reward.cumulative_score.toFixed(1)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
