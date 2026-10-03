/** The state of the "Ask the copilot" form. It lives here (not in actions/copilot.ts) because a "use server" file can only export functions. */
export type AskState = {
  question: string;
  answer: string | null;
  toolsUsed: { tool: string }[];
  generatedBy: string | null;
  error: string | null;
};

export const emptyAskState: AskState = { question: "", answer: null, toolsUsed: [], generatedBy: null, error: null };
