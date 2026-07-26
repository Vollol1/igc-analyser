-- SQLite schema for igc-extractor import/validation stage.
-- This database stores flight metadata, downloaded IGC file hashes and
-- a per-run validation/import summary.

PRAGMA foreign_keys = ON;

-- Flights known from flights.jsonl plus the results of IGC validation.
CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    IDFlight TEXT NOT NULL UNIQUE,
    FlightDate TEXT,
    TakeoffLocation TEXT,
    LandingLocation TEXT,
    Glider TEXT,
    BestTaskDistance REAL,
    FlightDuration INTEGER,
    IgcFilename TEXT,
    IgcFileHash TEXT,
    DownloadedAt TEXT,
    Valid TEXT NOT NULL CHECK (Valid IN ('valid', 'invalid', 'missing')),
    ValidationReason TEXT,
    LastUpdated TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_flights_valid ON flights(Valid);
CREATE INDEX IF NOT EXISTS idx_flights_idflight ON flights(IDFlight);

-- Per-run statistics (one row per import_flights.py invocation).
CREATE TABLE IF NOT EXISTS flight_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    total INTEGER NOT NULL,
    valid INTEGER NOT NULL,
    invalid INTEGER NOT NULL,
    missing INTEGER NOT NULL,
    downloaded INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL
);
