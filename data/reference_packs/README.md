# Permitted frozen reference subsets

These are **genuine source records**, not synthetic fixtures. They are never loaded automatically. The synthetic demo remains under `fixtures/evidence/`. Use the normal migrated PostgreSQL database and explicit CLI:

```powershell
python -m shiftos.cli ingest-evidence --dataset C-ESCO-V103 --file data/reference_packs/esco-v1.0.3.subset.reviewed.json --retrieved-at 2026-10-23T19:57:05.013428+00:00
python -m shiftos.cli ingest-evidence --dataset F-UN-SDG-RES70-1 --file data/reference_packs/un-sdg-resolution.reviewed.json --retrieved-at 2026-10-23T19:45:53.947292+00:00
```

Original retrieval assertions, checksums, exact source locators, source languages, adaptations and rights decisions are embedded in each manifest. The version checksum hashes the reviewed manifest; original source hashes remain separate. A `reviewed` flag means an engineering source check, not independent academic review or programme alignment.

**ESCO:** This service uses the ESCO classification of the European Commission. This is an adapted, bounded **v1.0.3 legacy multilingual subset**: 38 occupations, 10 skills with genuine English descriptions and 39 published relationships. Four occupation labels are source-English; 34 retain source-Arabic. Source CSV descriptions were empty; descriptions were recovered only from complete linked English resource blocks in a partial same-edition Turtle retrieval. The selected source blocks are included; the full Turtle archive was **not** downloaded or CRC-verified. The complete Arabic CSV ZIP passed integrity checks. Exact source URLs/hashes/range and reuse acknowledgement/adaptation terms are preserved. No translation, currentness, Malaysian classification bridge, demand observation or university teaching claim is implied. [Official reuse conditions](https://esco.ec.europa.eu/en/about-esco/faq?page=1).

**United Nations:** 17 goals and 169 targets transcribed from official resolution **A/RES/70/1**, issued 21 October 2015 (adopted 25 September). Original wording and identifiers are preserved; line wrapping and footnote markers are handled explicitly. The source is the official UN document, treated as public domain under [UN Publications Policy Manual 2020](https://uncitral.un.org/sites/default/files/media-documents/uncitral/en/policy_manual_rev_sept_2020.pdf), sections 5.34–5.35(c), not a separate sales publication or the statistical API/database. Section 5.37's separate database permission is not assumed. No UN endorsement, logo or occupation/skill-to-SDG relationship is claimed. Attribution and exact PDF pages/hash are in the manifest.

Restricted MQA/other research originals and narrowly reviewed internal cards remain in private local acquisition storage; this directory does not mirror them or assert a general redistribution licence. See the ingestion report for their actual queryable validation coverage and restrictions.
