"""
Run history storage using SQLite.
Stores historical monitoring runs for trend analysis.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class RunRecord:
    """A single monitoring run record."""
    run_id: str
    timestamp: datetime
    data_source: str
    hallucination_rate: float
    contradiction_rate: float
    schema_validity_rate: float
    evidence_validity_rate: float
    extraction_volume: float
    uncertainty_rate: float
    canary_f1: Optional[float]
    canary_action: Optional[str]
    alert_count: int
    critical_count: int


class RunHistoryDB:
    """SQLite-based storage for monitoring run history."""
    
    def __init__(self, db_path: Path = None):
        """
        Initialize the run history database.
        
        Args:
            db_path: Path to SQLite database. Defaults to out/run_history.db
        """
        if db_path is None:
            db_path = Path("out/run_history.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    data_source TEXT,
                    hallucination_rate REAL,
                    contradiction_rate REAL,
                    schema_validity_rate REAL,
                    evidence_validity_rate REAL,
                    extraction_volume REAL,
                    uncertainty_rate REAL,
                    canary_f1 REAL,
                    canary_action TEXT,
                    alert_count INTEGER,
                    critical_count INTEGER,
                    full_report TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_timestamp 
                ON runs(timestamp)
            """)
            
            conn.commit()
    
    def save_run(
        self,
        run_id: str,
        invariant_report,
        drift_report,
        canary_report=None,
        data_source: str = ""
    ):
        """
        Save a monitoring run to the database.
        
        Args:
            run_id: Unique run identifier
            invariant_report: InvariantReport object
            drift_report: DriftReport object
            canary_report: Optional CanaryReport object
            data_source: Description of data source
        """
        # Extract metrics from drift report
        extraction_vol = 0
        uncertainty = 0
        for metric in drift_report.metrics:
            if metric.name == "extraction_volume":
                extraction_vol = metric.current_value
            elif metric.name == "uncertainty_rate":
                uncertainty = metric.current_value
        
        # Count alerts
        all_alerts = invariant_report.alerts + drift_report.alerts
        critical_count = sum(1 for a in all_alerts if "CRITICAL" in a)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO runs (
                    run_id, timestamp, data_source,
                    hallucination_rate, contradiction_rate,
                    schema_validity_rate, evidence_validity_rate,
                    extraction_volume, uncertainty_rate,
                    canary_f1, canary_action,
                    alert_count, critical_count, full_report
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                datetime.now().isoformat(),
                data_source,
                invariant_report.hallucination_rate,
                invariant_report.contradiction_rate,
                invariant_report.schema_validity_rate,
                invariant_report.evidence_validity_rate,
                extraction_vol,
                uncertainty,
                canary_report.f1 if canary_report else None,
                canary_report.action.value if canary_report else None,
                len(all_alerts),
                critical_count,
                json.dumps({
                    "invariant": invariant_report.model_dump() if hasattr(invariant_report, 'model_dump') else {},
                    "drift": drift_report.model_dump() if hasattr(drift_report, 'model_dump') else {}
                }, default=str)
            ))
            
            # Save alerts
            for alert in all_alerts:
                severity = "CRITICAL" if "CRITICAL" in alert else "WARNING"
                conn.execute("""
                    INSERT INTO alerts (run_id, severity, message, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (run_id, severity, alert, datetime.now().isoformat()))
            
            conn.commit()
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        """Get the most recent runs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT run_id, timestamp, data_source,
                       hallucination_rate, contradiction_rate,
                       canary_f1, canary_action, alert_count, critical_count
                FROM runs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trend(self, metric: str, days: int = 7) -> List[Dict]:
        """Get trend data for a specific metric over the last N days."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT timestamp, {metric} as value
                FROM runs
                WHERE timestamp >= datetime('now', '-{days} days')
                ORDER BY timestamp ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_alert_summary(self, days: int = 7) -> Dict:
        """Get alert summary for the last N days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT severity, COUNT(*) as count
                FROM alerts
                WHERE timestamp >= datetime('now', '-? days')
                GROUP BY severity
            """, (days,))
            results = cursor.fetchall()
            return {row[0]: row[1] for row in results}
