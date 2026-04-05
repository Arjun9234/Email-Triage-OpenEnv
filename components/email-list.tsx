"use client";

import { Email } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface EmailListProps {
  emails: Email[];
  currentEmailId: string | null;
  onSelectEmail: (email: Email) => void;
}

export function EmailList({
  emails,
  currentEmailId,
  onSelectEmail,
}: EmailListProps) {
  const getActionBadge = (action?: string) => {
    const actionColors: Record<string, string> = {
      read: "bg-blue-500/20 text-blue-700 dark:text-blue-400",
      archive: "bg-gray-500/20 text-gray-700 dark:text-gray-400",
      delete: "bg-red-500/20 text-red-700 dark:text-red-400",
      flag: "bg-orange-500/20 text-orange-700 dark:text-orange-400",
      move_to_folder: "bg-purple-500/20 text-purple-700 dark:text-purple-400",
      mark_spam: "bg-pink-500/20 text-pink-700 dark:text-pink-400",
    };

    if (!action) return null;

    return (
      <Badge variant="secondary" className={actionColors[action]}>
        {action.replace("_", " ")}
      </Badge>
    );
  };

  return (
    <Card className="flex flex-col border-border/30 bg-card/40 backdrop-blur h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Inbox ({emails.length})</CardTitle>
      </CardHeader>

      <CardContent className="flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="space-y-2 px-4 pb-4">
            {emails.map((email) => (
              <button
                key={email.id}
                onClick={() => onSelectEmail(email)}
                className={cn(
                  "w-full text-left p-3 rounded-lg transition-all duration-200 border",
                  currentEmailId === email.id
                    ? "border-accent/50 bg-accent/20 ring-1 ring-accent/50"
                    : "border-border/20 bg-card/30 hover:bg-card/50 hover:border-border/40"
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-xs text-muted-foreground truncate">
                    {email.sender}
                  </p>
                  {email.has_attachment && <span className="text-xs">📎</span>}
                </div>
                <p className="text-sm font-medium text-foreground truncate mb-2">
                  {email.subject}
                </p>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={cn(
                      "inline-block px-2 py-0.5 rounded text-xs font-medium",
                      email.priority === "high"
                        ? "bg-red-500/20 text-red-700 dark:text-red-400"
                        : email.priority === "medium"
                          ? "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400"
                          : "bg-blue-500/20 text-blue-700 dark:text-blue-400"
                    )}
                  >
                    {email.priority}
                  </span>
                  {email.action_taken && (
                    <div>{getActionBadge(email.action_taken)}</div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
