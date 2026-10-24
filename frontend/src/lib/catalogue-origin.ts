export function catalogueHost(url: string | null | undefined) {
  try {
    return url ? new URL(url).hostname.replace(/^www\./, "") : null;
  } catch {
    return null;
  }
}

export function validatePdfOrigin(
  programmeUrl: string | null | undefined,
  institutionUrl: string | null | undefined,
  sourceUrl = "",
) {
  if (!programmeUrl || !institutionUrl)
    return "The institution website and official programme URL must be configured before an attributed PDF upload. Use reviewed input or ask your administrator to confirm the catalogue origins.";
  try {
    const host = catalogueHost(institutionUrl);
    const origins = [new URL(programmeUrl)];
    if (sourceUrl.trim()) origins.push(new URL(sourceUrl.trim()));
    if (
      host &&
      origins.every(
        (origin) =>
          origin.protocol === "https:" &&
          !origin.username &&
          !origin.password &&
          (!origin.port || origin.port === "443") &&
          origin.hostname.replace(/^www\./, "") === host,
      )
    )
      return null;
  } catch {
    // The backend remains authoritative; no origin is changed automatically.
  }
  return "The programme URL and any document URL must use the institution’s authorised HTTPS host. For a real university PDF, select the correct authorised institution and programme instead of placing it in a fictional demo. Ask the workspace administrator to confirm the origins; they are not changed automatically.";
}
