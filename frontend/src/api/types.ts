import type { components } from "./generated";
export type Model<K extends keyof components["schemas"]> =
  components["schemas"][K];
export type AccessContext = Model<"AccessContext">;
export type Programme = Model<"ProgrammeRead">;
export type Institution = Model<"InstitutionRead">;
export type Revision = Model<"ProgrammeRevisionRead">;
export type Course = Model<"CourseRead">;
export type CareerRun = Model<"CareerRead">;
export type CareerResult = Model<"CareerResult">;
export type PlanRun = Model<"PlanRead">;
export type PlanResult = Model<"PlanResult">;
export type Evidence = Model<"EvidenceItem">;
export type Citation = { reference_id: string; quote?: string };
export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};
export const isPending = (status?: string) =>
  status === "QUEUED" || status === "RUNNING";
export const humanise = (text: string) => text.replaceAll("_", " ");
export const dateLabel = (text?: string | null) =>
  text
    ? new Intl.DateTimeFormat("en-MY", { dateStyle: "medium" }).format(
        new Date(text),
      )
    : "Date not recorded";
export const revisionLabel = (revision: Revision) =>
  /^catalogue-[a-f\d]{64}$/i.test(revision.version_label)
    ? `Imported ${new Intl.DateTimeFormat("en-MY", { dateStyle: "medium", timeStyle: "short" }).format(new Date(revision.created_at))}`
    : revision.version_label;
