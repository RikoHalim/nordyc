import { createContext, useContext } from "react";
import type { ApiClient } from "../api/client";
import type { AccessContext } from "../api/types";
export type Session = {
  api: ApiClient;
  access: AccessContext;
  disconnect: () => void;
};
export const SessionContext = createContext<Session | null>(null);
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("Workspace access is required.");
  return session;
}
