"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Task } from "@/lib/api";

interface TaskSelectorProps {
  tasks: Task[];
  selectedTask: string | null;
  onSelectTask: (taskId: string) => Promise<void>;
  isLoading?: boolean;
}

const taskIcons: Record<string, string> = {
  easy: "🟢",
  medium: "🟡",
  hard: "🔴",
};

export function TaskSelector({
  tasks,
  selectedTask,
  onSelectTask,
  isLoading,
}: TaskSelectorProps) {
  return (
    <Card className="border-border/30 bg-card/40 backdrop-blur">
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Select Task</CardTitle>
      </CardHeader>

      <CardContent>
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
          {tasks.map((task) => (
            <Button
              key={task.id}
              variant={selectedTask === task.id ? "default" : "outline"}
              className={cn(
                "h-auto flex-col items-start gap-2 p-4 text-left transition-all duration-200",
                selectedTask === task.id && "ring-2 ring-accent/50"
              )}
              onClick={() => onSelectTask(task.id)}
              disabled={isLoading}
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">{taskIcons[task.id] || "📧"}</span>
                <span className="font-semibold">{task.name}</span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {task.description}
              </p>
              <span className="text-xs font-medium mt-1">
                {task.email_count} emails
              </span>
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
