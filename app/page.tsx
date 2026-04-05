"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { TaskSelector } from "@/components/task-selector";
import { EmailDisplay } from "@/components/email-display";
import { ActionButtons } from "@/components/action-buttons";
import { StatsPanel } from "@/components/stats-panel";
import { FeedbackPanel } from "@/components/feedback-panel";
import { EmailList } from "@/components/email-list";
import { emailTriageAPI, Observation, Reward, State, Task, GradeResponse, Email } from "@/lib/api";

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [observation, setObservation] = useState<Observation | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [reward, setReward] = useState<Reward | null>(null);
  const [gradeResult, setGradeResult] = useState<GradeResponse | null>(null);
  const [currentEmail, setCurrentEmail] = useState<Email | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(false);

  // Load available tasks
  useEffect(() => {
    const loadTasks = async () => {
      try {
        const response = await emailTriageAPI.getTasks();
        setTasks(response.tasks);

        const restored = await emailTriageAPI.restoreSession();
        if (restored) {
          setSelectedTask(restored.state.task);
          setObservation(restored.observation);
          setState(restored.state);
          setCurrentEmail(restored.observation.current_email);
          setIsDone(Boolean(restored.state.done));

          if (restored.state.done) {
            try {
              const grade = await emailTriageAPI.grade();
              setGradeResult(grade);
            } catch (gradeErr) {
              console.error("Error restoring grade:", gradeErr);
            }
          }
        } else if (response.tasks.length > 0) {
          setSelectedTask(response.tasks[0].id);
        }

        setIsDemo(emailTriageAPI.isUsingMockAPI());
      } catch (err) {
        setIsDemo(true);
        setError(null);
        console.error("Error loading tasks:", err);
        // Retry with mock API
        const mockResponse = await emailTriageAPI.getTasks();
        setTasks(mockResponse.tasks);
        if (mockResponse.tasks.length > 0) {
          setSelectedTask(mockResponse.tasks[0].id);
        }
      }
    };

    loadTasks();
  }, []);

  // Real-time polling for backend updates (Hugging Face models, etc.)
  useEffect(() => {
    if (!observation) return; // Only poll when task is active

    // Subscribe to real-time updates from backend
    const unsubscribe = emailTriageAPI.subscribeToUpdates(2000, (updatedObs) => {
      // Update observation and state with latest from backend
      setObservation(updatedObs);

      // Fetch latest state to get updated scores
      emailTriageAPI.getState().then((newState) => {
        setState(newState);

        // Update current email if it changed in the observation
        if (updatedObs.current_email) {
          setCurrentEmail(updatedObs.current_email);
        }
      }).catch((err) => {
        console.error("Error fetching state:", err);
      });
    });

    return () => {
      unsubscribe(); // Cleanup polling on unmount or task change
    };
  }, [observation]); // Re-setup when observation changes

  const handleSelectTask = async (taskId: string) => {
    setIsLoading(true);
    setError(null);
    setReward(null);
    setGradeResult(null);
    setIsDone(false);

    try {
      const response = await emailTriageAPI.reset(taskId);
      setSelectedTask(taskId);
      setObservation(response.observation);
      setState(response.state);
      setCurrentEmail(response.observation.current_email);
      setIsDemo(emailTriageAPI.isUsingMockAPI());
    } catch (err) {
      setError("Failed to reset environment. Please try again.");
      console.error("Error resetting environment:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (action: string) => {
    if (!currentEmail || !observation) {
      setError("No email selected");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await emailTriageAPI.step(action, currentEmail.id);
      setObservation(response.observation);
      setState(response.state);
      setReward(response.reward);
      setCurrentEmail(response.observation.current_email);
      setIsDemo(emailTriageAPI.isUsingMockAPI());

      if (response.done) {
        setIsDone(true);
        try {
          const grade = await emailTriageAPI.grade();
          setGradeResult(grade);
        } catch (gradeErr) {
          console.error("Error grading:", gradeErr);
        }
      }
    } catch (err) {
      setError("Failed to execute action. Is the backend running?");
      console.error("Error executing action:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectEmail = (email: Email) => {
    setCurrentEmail(email);
    setReward(null);
  };

  const handleReset = () => {
    setObservation(null);
    setState(null);
    setReward(null);
    setGradeResult(null);
    setCurrentEmail(null);
    setIsDone(false);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-neutral-50/50 dark:bg-neutral-950 text-foreground">
      {/* Top Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-7xl mx-auto flex h-16 items-center px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4"><path d="M21.2 8.4c.5.38.8.97.8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 .8-1.6l8-6a2 2 0 0 1 2.4 0l8 6Z"/><path d="m22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10"/></svg>
            </div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-neutral-900 to-neutral-500 dark:from-neutral-100 dark:to-neutral-500 bg-clip-text text-transparent">
              Email Triage OpenEnv
            </h1>
            {isDemo && (
              <span className="ml-2 inline-flex items-center rounded-full border border-blue-200/50 bg-blue-50/50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 shadow-sm backdrop-blur-sm dark:border-blue-800/50 dark:bg-blue-900/30 dark:text-blue-300">
                <span className="mr-1.5 flex h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                Demo Backend
              </span>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        {/* Intro Section */}
        <div className="mb-8">
          <p className="text-muted-foreground text-sm sm:text-base max-w-2xl">
            Interactive benchmark for evaluating deterministic and LLM-driven email management strategies.
          </p>
          {error && (
            <div className="mt-4 rounded-xl bg-destructive/10 border border-destructive/20 p-4 text-sm text-destructive flex gap-3 shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 shrink-0 mt-0.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <div>
                <p className="font-semibold mb-1">Connection Error</p>
                <p>{error}</p>
                <p className="text-xs mt-2 opacity-80">Ensure `python server/main.py` is running with active FastAPI server.</p>
              </div>
            </div>
          )}
        </div>

        <div className="mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <TaskSelector
            tasks={tasks}
            selectedTask={selectedTask}
            onSelectTask={handleSelectTask}
            isLoading={isLoading}
          />
        </div>

        {observation && state ? (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700 fill-mode-both">
            {/* Stats */}
            <StatsPanel state={state} />

            {/* Main Grid */}
            <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
              {/* Left: Email List */}
              <div className="lg:col-span-1 h-[500px] sm:h-[650px] shadow-sm rounded-xl overflow-hidden border border-border/40 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/40">
                <EmailList
                  emails={observation.email_list}
                  currentEmailId={currentEmail?.id || null}
                  onSelectEmail={handleSelectEmail}
                />
              </div>

              {/* Center: Email Display */}
              <div className="lg:col-span-1 h-[500px] sm:h-[650px] shadow-sm rounded-xl overflow-hidden border border-border/40 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/40">
                <EmailDisplay
                  email={currentEmail}
                  isLoading={isLoading && !currentEmail}
                />
              </div>

              {/* Right: Actions & Feedback */}
              <div className="lg:col-span-1 flex flex-col gap-6 h-[500px] sm:h-[650px]">
                <div className="flex-none shadow-sm rounded-xl overflow-hidden">
                  <ActionButtons
                    emailId={currentEmail?.id || null}
                    onAction={handleAction}
                    isLoading={isLoading}
                    disabled={isDone}
                  />
                </div>

                <div className="flex-1 shadow-sm rounded-xl overflow-hidden min-h-0">
                  <FeedbackPanel
                    reward={reward}
                    gradeResult={gradeResult}
                    isLoading={isLoading && !reward}
                    isDone={isDone}
                  />
                </div>
              </div>
            </div>

            {/* Footer Actions */}
            <div className="flex gap-4 justify-center sm:justify-start pt-4 border-t border-border/40">
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={isLoading}
                className="gap-2 shadow-sm rounded-full px-6"
              >
                Choose New Task
              </Button>
              {isDone && (
                <Button
                  variant="default"
                  onClick={handleReset}
                  className="gap-2 shadow-sm rounded-full px-6 bg-primary/90 hover:bg-primary"
                >
                  Restart Current Task
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center min-h-[400px] rounded-xl border border-dashed border-border/50 bg-neutral-100/50 dark:bg-neutral-900/20">
            <div className="text-center space-y-3">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-neutral-200/50 dark:bg-neutral-800/50">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-muted-foreground"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              </div>
              <p className="text-muted-foreground font-medium">
                {error
                  ? "Backend is offline. Check connection."
                  : "Select a triage scenario pattern above to begin."}
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer className="mt-8 border-t border-border/20 py-8 bg-background/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center text-xs text-muted-foreground gap-4">
          <p>OpenEnv Email Triage Benchmark v2.0</p>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <p>Ready @ {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
