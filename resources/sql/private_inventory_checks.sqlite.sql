-- Read-only local inventory checks. Bind :owner to the operator's user ID.
-- Canonical data is identified_spots in data/local-research.db; no shadow writable DB.

SELECT id, name, category, area, status, venue_id,
       json_extract(data, '$.maps_identity.confirmed_by') AS maps_reviewed_by
FROM identified_spots WHERE user_id = :owner AND status NOT IN ('merged', 'quarantined', 'rejected')
ORDER BY name, area;

-- The identity_key column already has a SQL UNIQUE constraint.
SELECT identity_key, COUNT(*) AS copies FROM identified_spots
WHERE user_id = :owner GROUP BY identity_key HAVING COUNT(*) > 1;

-- Any duplicate explicit Maps place identity needs consolidation/review.
SELECT json_extract(data, '$.maps_identity.place_key') AS place_key, COUNT(*) AS copies
FROM identified_spots WHERE user_id = :owner
AND status NOT IN ('merged', 'quarantined', 'rejected')
AND json_extract(data, '$.maps_identity.place_key') IS NOT NULL
GROUP BY place_key HAVING COUNT(*) > 1;

-- Early-exit receipts retain source records without pretending the clip was fully read.
SELECT s.id, s.canonical_url, json_extract(s.analysis, '$.discovery_skip.stage') AS stopped_at
FROM research_sources s JOIN investigations i ON s.case_id=i.id
WHERE i.user_id=:owner AND json_extract(s.analysis, '$.discovery_skip') IS NOT NULL;
