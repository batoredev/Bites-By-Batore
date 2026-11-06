# Spot identity and relevance checks

Updated 6 November 2026 (Asia/Calcutta). This extends the Instagram inventory pipeline; it does not declare the complete Instagram vision finished.

## What changed

The previous key used only the extracted name and area. Missing areas, punctuation and alternate names therefore produced duplicate records. Repeated collection timestamps also produced repeated source entries. Model outputs sometimes promoted generic captions, dishes, creator handles, nearby landmarks and out-of-city locations into venue candidates. Older multi-venue reels copied all observations into every candidate.

The new path checks an extraction before inserting an identified spot:

1. Normalize spacing, underscores, Latin accents and punctuation for comparison while retaining original display names/aliases. Preserve Tamil combining marks. Normalize neighbourhood variants such as `R.S. Puram`.
2. Hold generic/promotional names, relative descriptions such as `cafe near VOC Park`, obvious out-of-scope address evidence, speech-only names without corroborating modalities, and possible landmark misattributions. Held extraction decisions and reasons remain in the investigation's `inventory_checks`.
3. Search the owner's existing inventory. Equivalent names can share a draft when compatible branch evidence supports the match. Explicit conflicting branch keys, addresses, house numbers, postcodes or known neighbourhoods block automatic merges. Identical names in different posts with no branch evidence remain separate proposals rather than becoming a falsely confirmed single branch.
4. Treat spelling similarity as a review suggestion. Do not automatically merge typo matches, arbitrary branch alternatives or separate owners' records.
5. Merge evidence by source and meaning. A source refresh updates collection dates rather than creating another identical source row. Different prices and conflicting facts remain proposals; they are not silently overwritten.
6. Associate observations with the named venue in multi-venue content. Existing ambiguous observations/vibes move to unassigned evidence, retaining their original source links.
7. At investigation completion, reconcile the owner's inventory again. Merged and quarantined records are excluded from the default active list and skipped by enrichment jobs, but retained for review/export/erasure.

These are conservative rules, not a validated universal relevance classifier. They can hold a legitimate unusual name. The operator can resolve a false positive using independent branch evidence and an explicit Maps identity review; the reviewed warnings remain recorded. Raw model outputs are not accepted venue facts.

## Maps names and exact branches

Extracted names are labelled **Maps identity unconfirmed**. A generic Maps search link does not confirm a place.

Preparing a non-demo location requires the operator to check the name and exact Maps branch, supply a specific Google place link, and provide independent branch evidence, address and coordinates within the current Coimbatore boundary. Place-ID and CID references are accepted; short links must be opened to their full URL. Search-only and coordinate-only links do not qualify. Existing venue/place identities are checked to prevent a second prepared venue for the same reference.

Canonical reviewed names replace draft display names and previous spellings remain aliases. The confirmation records its operator, time, reference and basis. It is an **operator assertion**, not proof that an API verified the spelling or that the venue is open. Names and current venue facts still need independent evidence.

The optional **Look up Maps candidates** action uses the existing Google Places connector, filters returned coordinates to the Coimbatore boundary, displays fresh results with attribution and does not persist the API name/address payload. Missing access is explicit and leaves the name unconfirmed. No live Maps API success is claimed for this update. Public Instagram collection continues without that API.

Google's [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies) restrict caching of API content and allow storage of place IDs. [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started) provide precise place linking without an API key. The app does not treat an API key's presence or an arbitrary URL as verification.

Venue desk also supports Maps identity confirmation/correction for manually created or previously prepared records. Changing a published identity returns the venue to pending and removes its previous location approval. Publication and planning require operator location approval, Maps identity review and the existing essential-fact checks. No venue was approved on the user's behalf.

## Operator workflow

1. Open `/admin` → **Identified spots**. The default list contains active drafts.
2. Use **Show held and merged records** to inspect excluded records, reasons and original evidence. Use **Check duplicates and relevance** to repeat the idempotent cleanup.
3. Inspect flagged possible duplicates against the exact address/branch. **Merge duplicate after branch check** requires choosing the surviving draft, confirming the same branch and recording a reason. Evidence and original records remain; prepared venues cannot be merged through this draft action.
4. In **Prepare location for approval**, check the Maps name and precise place link along with independent address/coordinate evidence. This creates a pending venue, not a suggestion.
5. Review current essential facts in Venue desk, then explicitly approve the location. A Maps identity change requires approval again.

Owner-specific spot reviews, merged records and quarantined records are included in export and erasure. Published venue audits follow the existing shared venue lifecycle. Point-in-time backups are separate from active-database erasure.

Local CLI, from `backend`:

```powershell
uv run python -m app.manage check-spots
# Review the preview and take a snapshot before maintenance.
uv run python -m app.manage backup-demo
uv run python -m app.manage clean-spots
```

`check-spots` rolls back its preview. `clean-spots` commits the cleanup for the local operator. Neither publishes a location or deletes source investigations.

## Real cleanup checkpoint

At 10:59:16 IST on 6 November, cleanup of the existing 66 records:

- Merged 8 duplicate drafts into surviving records.
- Held 22 records for relevance/identity review, including generic titles, Chennai address evidence, likely landmarks and speech-only names.
- Removed 15 repeated list entries and set aside 31 ambiguous observation/vibe associations.
- Left 36 active candidates, not 36 verified venues. All 66 originals remain stored.
- Repeating the cleanup made zero changes. Zero real venues were published.

Evidence: ignored `data/spot-quality-cleanup-2026-11-06.json`. Continuous collection can change counts after this checkpoint.

A real local-model smoke used two synthetic captions without any inventory writes. It exposed an unnamed-landmark description passing the first filter; the relative-description rule and a regression case were then added. Replaying the saved output through the repaired filter yields zero eligible candidates. This is not a measured accuracy benchmark or real Maps verification. Evidence: `data/spot-quality-local-model-smoke.json`.

## Remaining original-plan work

Automatic exact-branch identity evaluation, advanced visual reference-image matching, calibrated creator reliability, broader accessible comments/replies, representative multilingual transcription/OCR/analysis accuracy, verified current city inventory and customer validation remain open. Optional Meta/Apify/Google account paths are not live merely because code exists. Local third-party model weights and retrieved reviewer corrections are not owned trained weights.
