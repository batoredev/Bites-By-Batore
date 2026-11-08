-- Generated empty-database schema, not an upgrade or private-data dump.

-- Use python -m app.manage migrate for existing databases.

BEGIN;

CREATE TABLE audit (
	id VARCHAR NOT NULL, 
	actor VARCHAR NOT NULL, 
	action VARCHAR NOT NULL, 
	target VARCHAR NOT NULL, 
	detail JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE claims (
	id VARCHAR NOT NULL, 
	venue_id VARCHAR NOT NULL, 
	field VARCHAR NOT NULL, 
	value JSON NOT NULL, 
	source_url TEXT NOT NULL, 
	source_type VARCHAR NOT NULL, 
	source_group VARCHAR NOT NULL, 
	observed_at VARCHAR NOT NULL, 
	fetched_at VARCHAR NOT NULL, 
	expires_at VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	reason TEXT NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE counters (
	key VARCHAR NOT NULL, 
	value INTEGER NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE demo_sessions (
	token_hash VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	expires_at VARCHAR NOT NULL, 
	PRIMARY KEY (token_hash)
);

CREATE TABLE dish_entries (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	venue_id VARCHAR NOT NULL, 
	offering_key VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	note TEXT NOT NULL, 
	tried_on VARCHAR, 
	preferences JSON NOT NULL, 
	updated_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE identified_spots (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	identity_key VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	area VARCHAR NOT NULL, 
	data JSON NOT NULL, 
	status VARCHAR NOT NULL, 
	venue_id VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	updated_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (identity_key)
);

CREATE TABLE investigations (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	query VARCHAR NOT NULL, 
	context JSON NOT NULL, 
	state VARCHAR NOT NULL, 
	result JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	updated_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE jobs (
	id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	payload JSON NOT NULL, 
	state VARCHAR NOT NULL, 
	attempts INTEGER NOT NULL, 
	priority INTEGER NOT NULL, 
	due_at VARCHAR NOT NULL, 
	lease_until VARCHAR, 
	error TEXT NOT NULL, 
	result JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	completed_at VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (key)
);

CREATE TABLE plans (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	request JSON NOT NULL, 
	result JSON NOT NULL, 
	saved BOOLEAN NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE research_corrections (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	source_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	scope VARCHAR NOT NULL, 
	original TEXT NOT NULL, 
	corrected TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE research_sources (
	id VARCHAR NOT NULL, 
	case_id VARCHAR NOT NULL, 
	canonical_url TEXT NOT NULL, 
	platform VARCHAR NOT NULL, 
	creator VARCHAR NOT NULL, 
	content JSON NOT NULL, 
	analysis JSON NOT NULL, 
	state VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE research_tasks (
	id VARCHAR NOT NULL, 
	case_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	ordinal INTEGER NOT NULL, 
	state VARCHAR NOT NULL, 
	result JSON NOT NULL, 
	error TEXT NOT NULL, 
	completed_at VARCHAR, 
	PRIMARY KEY (id)
);

CREATE TABLE saved_venues (
	user_id VARCHAR NOT NULL, 
	venue_id VARCHAR NOT NULL, 
	PRIMARY KEY (user_id, venue_id)
);

CREATE TABLE schema_migrations (
	version SERIAL NOT NULL, 
	description VARCHAR NOT NULL, 
	applied_at VARCHAR NOT NULL, 
	PRIMARY KEY (version)
);

CREATE TABLE source_assessments (
	id VARCHAR NOT NULL, 
	source_id VARCHAR NOT NULL, 
	creator_identity VARCHAR NOT NULL, 
	evidence_group VARCHAR NOT NULL, 
	outcome VARCHAR NOT NULL, 
	reason TEXT NOT NULL, 
	evidence_url TEXT NOT NULL, 
	actor VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE submissions (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	url TEXT NOT NULL, 
	content JSON NOT NULL, 
	result JSON NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	profile JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE venues (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	area VARCHAR NOT NULL, 
	address VARCHAR NOT NULL, 
	lat FLOAT NOT NULL, 
	lng FLOAT NOT NULL, 
	tags JSON NOT NULL, 
	details JSON NOT NULL, 
	status VARCHAR NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	revision INTEGER NOT NULL, 
	updated_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE visits (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	venue_id VARCHAR NOT NULL, 
	rating INTEGER NOT NULL, 
	dimensions JSON NOT NULL, 
	note TEXT NOT NULL, 
	occasion VARCHAR NOT NULL, 
	visited_on VARCHAR NOT NULL, 
	experience JSON NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_audit_owner_action ON audit (actor, action);

ALTER TABLE "audit" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_claim_current ON claims (venue_id, status, expires_at);

CREATE INDEX ix_claims_status ON claims (status);

CREATE INDEX ix_claims_venue_id ON claims (venue_id);

ALTER TABLE "claims" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "counters" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_demo_sessions_user_id ON demo_sessions (user_id);

ALTER TABLE "demo_sessions" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_dish_entries_user_id ON dish_entries (user_id);

CREATE INDEX ix_dish_entries_venue_id ON dish_entries (venue_id);

CREATE UNIQUE INDEX uq_dish_owner_venue_item ON dish_entries (user_id, venue_id, offering_key);

ALTER TABLE "dish_entries" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_identified_spots_status ON identified_spots (status);

CREATE INDEX ix_identified_spots_user_id ON identified_spots (user_id);

CREATE INDEX ix_spot_owner_status ON identified_spots (user_id, status);

ALTER TABLE "identified_spots" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_case_owner_state ON investigations (user_id, state);

CREATE INDEX ix_investigations_state ON investigations (state);

CREATE INDEX ix_investigations_user_id ON investigations (user_id);

ALTER TABLE "investigations" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_job_dispatch ON jobs (state, priority, due_at);

CREATE INDEX ix_job_recovery ON jobs (state, lease_until);

CREATE INDEX ix_jobs_due_at ON jobs (due_at);

CREATE INDEX ix_jobs_state ON jobs (state);

ALTER TABLE "jobs" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_plans_user_id ON plans (user_id);

ALTER TABLE "plans" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_research_corrections_source_id ON research_corrections (source_id);

CREATE INDEX ix_research_corrections_user_id ON research_corrections (user_id);

ALTER TABLE "research_corrections" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_research_sources_case_id ON research_sources (case_id);

CREATE UNIQUE INDEX uq_source_case_url ON research_sources (case_id, canonical_url);

ALTER TABLE "research_sources" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_research_tasks_case_id ON research_tasks (case_id);

CREATE UNIQUE INDEX uq_task_case_ordinal ON research_tasks (case_id, ordinal);

ALTER TABLE "research_tasks" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "saved_venues" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "schema_migrations" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_source_assessments_creator_identity ON source_assessments (creator_identity);

CREATE INDEX ix_source_assessments_evidence_group ON source_assessments (evidence_group);

CREATE INDEX ix_source_assessments_source_id ON source_assessments (source_id);

ALTER TABLE "source_assessments" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_submissions_user_id ON submissions (user_id);

ALTER TABLE "submissions" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "users" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_venues_category ON venues (category);

CREATE INDEX ix_venues_is_demo ON venues (is_demo);

CREATE INDEX ix_venues_status ON venues (status);

ALTER TABLE "venues" ENABLE ROW LEVEL SECURITY;

CREATE INDEX ix_visits_user_id ON visits (user_id);

CREATE UNIQUE INDEX uq_visit_owner_venue_date ON visits (user_id, venue_id, visited_on);

ALTER TABLE "visits" ENABLE ROW LEVEL SECURITY;

INSERT INTO counters (key,value) VALUES ('schema_version',7);

INSERT INTO schema_migrations (version,description,applied_at) VALUES (7,'Generated empty-database schema',CURRENT_TIMESTAMP);

COMMIT;
