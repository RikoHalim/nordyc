const logoPath = import.meta.env.VITE_BRAND_LOGO_PATH;
export const BRAND = {
  name: import.meta.env.VITE_BRAND_NAME || "NORDYC",
  descriptor: "Curriculum workspace",
  logo:
    typeof logoPath === "string" &&
    /^\/[A-Za-z\d/_.-]+$/.test(logoPath) &&
    !logoPath.startsWith("//") &&
    !logoPath.includes("..")
      ? logoPath
      : null,
};
export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className={`brand ${compact ? "compact" : ""}`}
      aria-label={BRAND.name}
    >
      {BRAND.logo ? (
        <img src={BRAND.logo} width="38" height="38" alt="" />
      ) : (
        <svg
          width="38"
          height="38"
          viewBox="0 0 38 38"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M3 12.5 19 4l16 8.5L19 21 3 12.5Z"
            stroke="currentColor"
            strokeWidth="2.4"
          />
          <path
            d="M8 16v12l11 6 11-6V16M19 10l10 5.5v7M19 21v7"
            stroke="currentColor"
            strokeWidth="2.4"
          />
          <path d="m8 18 11 6" stroke="#3574FF" strokeWidth="2.4" />
        </svg>
      )}
      <span>{BRAND.name}</span>
    </span>
  );
}
