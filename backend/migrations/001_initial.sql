-- Initial schema uses SQLAlchemy metadata; optional upgrade indexes:
CREATE INDEX window_study_split_idx ON climate_windows (study_id,split);
CREATE INDEX note_run_status_idx ON review_notes (run_id,status);
CREATE INDEX retraction_study_status_idx ON window_retractions (study_id,status);
