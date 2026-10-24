import { createContext, useContext } from "react";
import type { ApiClient } from "../api/client";
import type {
  AccessContext,
  Institution,
  Programme,
  Revision,
} from "../api/types";

export type WorkspaceContext = {
  api: ApiClient;
  access: AccessContext;
  programme: Programme;
  institution: Institution;
  revisionId: string | null;
  revisions: Revision[];
  setRevision: (id: string) => void;
};
export const Workspace = createContext<WorkspaceContext | null>(null);
export function useWorkspace() {
  const context = useContext(Workspace);
  if (!context) throw new Error("Programme context is required.");
  return context;
}
