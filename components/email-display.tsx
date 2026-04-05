"use client";

import { Email } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface EmailDisplayProps {
  email: Email | null;
  isLoading?: boolean;
}

export function EmailDisplay({ email, isLoading }: EmailDisplayProps) {
  if (isLoading) {
    return (
      <Card className="h-full border-border/30 bg-card/40 backdrop-blur">
        <CardHeader className="pb-4">
          <div className="h-6 w-32 animate-pulse rounded bg-muted" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    );
  }

  if (!email) {
    return (
      <Card className="flex h-full items-center justify-center border-border/30 bg-card/40 backdrop-blur">
        <div className="text-center">
          <p className="text-muted-foreground">No email selected</p>
        </div>
      </Card>
    );
  }

  const priorityColors: Record<string, string> = {
    high: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
    medium: "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border-yellow-500/30",
    low: "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30",
  };

  return (
    <Card className="flex h-full flex-col border-border/30 bg-card/40 backdrop-blur">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground truncate">{email.sender}</p>
            <h2 className="text-xl font-semibold text-foreground break-words mt-2">
              {email.subject}
            </h2>
          </div>
          <Badge
            variant="outline"
            className={`whitespace-nowrap ${priorityColors[email.priority]}`}
          >
            {email.priority.charAt(0).toUpperCase() + email.priority.slice(1)}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4">
        {email.has_attachment && (
          <div className="flex items-center gap-2 rounded-lg bg-accent/10 px-3 py-2 text-sm text-accent-foreground">
            <span>📎</span>
            <span>Has attachment</span>
          </div>
        )}

        <div className="flex-1">
          <p className="text-foreground/90 leading-relaxed whitespace-pre-wrap break-words">
            {email.preview}
          </p>
        </div>

        <div className="pt-4 border-t border-border/20 text-xs text-muted-foreground">
          <p>Email ID: {email.id}</p>
        </div>
      </CardContent>
    </Card>
  );
}
