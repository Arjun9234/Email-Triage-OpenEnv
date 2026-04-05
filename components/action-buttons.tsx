"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ActionButtonsProps {
  emailId: string | null;
  onAction: (action: string) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
}

const ACTIONS = [
  {
    id: "read",
    label: "Read",
    icon: "📖",
    description: "Process the email",
    variant: "default" as const,
  },
  {
    id: "archive",
    label: "Archive",
    icon: "📦",
    description: "Store for reference",
    variant: "outline" as const,
  },
  {
    id: "delete",
    label: "Delete",
    icon: "🗑️",
    description: "Remove email",
    variant: "outline" as const,
  },
  {
    id: "flag",
    label: "Flag",
    icon: "🚩",
    description: "Mark for action",
    variant: "outline" as const,
  },
  {
    id: "move_to_folder",
    label: "Move",
    icon: "📁",
    description: "Organize",
    variant: "outline" as const,
  },
  {
    id: "mark_spam",
    label: "Spam",
    icon: "🚫",
    description: "Report spam",
    variant: "outline" as const,
  },
];

export function ActionButtons({
  emailId,
  onAction,
  isLoading,
  disabled = false,
}: ActionButtonsProps) {
  return (
    <Card className="border-border/30 bg-card/40 backdrop-blur">
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Take Action</CardTitle>
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {ACTIONS.map((action) => (
            <Button
              key={action.id}
              variant={action.variant}
              size="sm"
              className={cn(
                "h-auto flex-col gap-1 py-3 transition-all duration-200",
                isLoading && "opacity-50 cursor-not-allowed"
              )}
              onClick={() => onAction(action.id)}
              disabled={!emailId || disabled || isLoading}
            >
              <span className="text-lg">{action.icon}</span>
              <span className="text-xs font-medium">{action.label}</span>
            </Button>
          ))}
        </div>

        {!emailId && (
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Reset to start triage
          </p>
        )}
      </CardContent>
    </Card>
  );
}
