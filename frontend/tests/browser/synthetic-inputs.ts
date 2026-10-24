/** Genuine tiny PDF adapted from tests/test_curriculum_pdf.py. Fictional text only. */
export function syntheticPdf(): Buffer {
  const lines: [number, number, string][] = [
    [50, 10, "Fictional curriculum - synthetic browser acceptance only"],
    [50, 30, "MAIN COURSES"],
    [50, 60, "Year 1"],
    [50, 80, "- Synthetic Review Foundations"],
    [50, 100, "- Synthetic Evidence Practice"],
    [330, 60, "Year 2"],
    [330, 80, "- Synthetic Academic Inquiry"],
  ];
  const stream = lines
    .map(
      ([x, y, value]) =>
        `BT /F1 10 Tf 1 0 0 1 ${x} ${792 - y} Tm (${value}) Tj ET`,
    )
    .join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`,
  ];
  let output = "%PDF-1.4\n";
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(Buffer.byteLength(output));
    output += `${index + 1} 0 obj\n${object}\nendobj\n`;
  }
  const xref = Buffer.byteLength(output);
  output += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1))
    output += `${String(offset).padStart(10, "0")} 00000 n \n`;
  output += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(output, "ascii");
}
export function reviewedManifest(name: string, canonicalUrl: string) {
  return {
    name,
    canonical_url: canonicalUrl,
    source_url: canonicalUrl,
    source_locator: "synthetic:browser-reviewed-transcription",
    retrieved_at: new Date().toISOString(),
    license_status: "synthetic_fixture",
    reviewed: true,
    is_synthetic: true,
    notes: [
      "Entirely fictional browser test; reviewed title transcription only, no learning outcome or teaching assertion.",
    ],
    courses: [
      "Synthetic Review Foundations",
      "Synthetic Evidence Practice",
      "Synthetic Academic Inquiry",
    ].map((course_name, index) => ({
      course_name,
      course_code: null,
      year: index === 2 ? 2 : 1,
      semester: null,
      course_type: "UNKNOWN",
      source_locator: `synthetic:browser-reviewed-course-${index + 1}`,
      source_excerpt: course_name,
      review_notes: [
        "Fictional title transcribed from the synthetic PDF. Content remains unknown.",
      ],
    })),
  };
}
