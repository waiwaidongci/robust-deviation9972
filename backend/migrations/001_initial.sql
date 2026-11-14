-- Initial schema uses SQLAlchemy metadata; optional upgrade indexes:
CREATE INDEX window_study_split_idx ON climate_windows (study_id,split);
CREATE INDEX note_run_status_idx ON review_notes (run_id,status);
