"""Persistent SQLite storage for all domain check results and scores."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class ResultsStore:
    """Stores all checked domains with availability and scores in SQLite."""
    
    def __init__(self, db_file: str = "data/results/domains.db"):
        self.db_file = Path(db_file)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    domain TEXT PRIMARY KEY,
                    word TEXT,
                    tld TEXT,
                    available INTEGER,
                    method TEXT,
                    error TEXT,
                    
                    -- Score fields
                    total_score REAL,
                    pronounceability INTEGER,
                    spellability INTEGER,
                    length_score INTEGER,
                    memorability INTEGER,
                    brandability INTEGER,
                    dictionary_score INTEGER,
                    tld_multiplier REAL,
                    
                    -- Timestamps
                    first_checked TEXT,
                    last_checked TEXT,
                    check_count INTEGER DEFAULT 1
                )
            """)
            
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_available ON domains(available)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_total_score ON domains(total_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tld ON domains(tld)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_word ON domains(word)")
            conn.commit()
    
    def _parse_domain(self, domain: str) -> tuple:
        """Extract word and TLD from domain."""
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            return parts[0], parts[-1]
        return domain, ''
    
    def add(
        self,
        domain: str,
        available: Optional[bool],
        method: str,
        score: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """Add or update a domain result."""
        word, tld = self._parse_domain(domain)
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_file) as conn:
            existing = conn.execute(
                "SELECT first_checked, check_count FROM domains WHERE domain = ?",
                (domain,)
            ).fetchone()
            
            if existing:
                first_checked, check_count = existing
                check_count += 1
            else:
                first_checked = now
                check_count = 1
            
            conn.execute("""
                INSERT OR REPLACE INTO domains (
                    domain, word, tld, available, method, error,
                    total_score, pronounceability, spellability, length_score,
                    memorability, brandability, dictionary_score, tld_multiplier,
                    first_checked, last_checked, check_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                domain, word, tld,
                1 if available is True else (0 if available is False else None),
                method, error,
                score.get("total_score") if score else None,
                score.get("pronounceability") if score else None,
                score.get("spellability") if score else None,
                score.get("length_score") if score else None,
                score.get("memorability") if score else None,
                score.get("brandability") if score else None,
                score.get("dictionary_score") if score else None,
                score.get("tld_multiplier") if score else None,
                first_checked, now, check_count
            ))
            conn.commit()
    
    def add_batch(self, results: List[Dict[str, Any]]):
        """Add multiple domain results at once."""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_file) as conn:
            for r in results:
                domain = r["domain"]
                word, tld = self._parse_domain(domain)
                score = r.get("score", {})
                
                existing = conn.execute(
                    "SELECT first_checked, check_count FROM domains WHERE domain = ?",
                    (domain,)
                ).fetchone()
                
                if existing:
                    first_checked, check_count = existing
                    check_count += 1
                else:
                    first_checked = now
                    check_count = 1
                
                available = r.get("available")
                conn.execute("""
                    INSERT OR REPLACE INTO domains (
                        domain, word, tld, available, method, error,
                        total_score, pronounceability, spellability, length_score,
                        memorability, brandability, dictionary_score, tld_multiplier,
                        first_checked, last_checked, check_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    domain, word, tld,
                    1 if available is True else (0 if available is False else None),
                    r.get("method", "unknown"), r.get("error"),
                    score.get("total_score"),
                    score.get("pronounceability"),
                    score.get("spellability"),
                    score.get("length_score"),
                    score.get("memorability"),
                    score.get("brandability"),
                    score.get("dictionary_score"),
                    score.get("tld_multiplier"),
                    first_checked, now, check_count
                ))
            conn.commit()
    
    def get(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get stored result for a domain."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM domains WHERE domain = ?", (domain,)
            ).fetchone()
            return dict(row) if row else None
    
    def query(
        self,
        available: Optional[bool] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        tld: Optional[str] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        order_by: str = "total_score DESC",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Flexible query for domains."""
        conditions = []
        params = []
        
        if available is not None:
            conditions.append("available = ?")
            params.append(1 if available else 0)
        
        if min_score is not None:
            conditions.append("total_score >= ?")
            params.append(min_score)
        
        if max_score is not None:
            conditions.append("total_score <= ?")
            params.append(max_score)
        
        if tld is not None:
            conditions.append("tld = ?")
            params.append(tld)
        
        if min_length is not None:
            conditions.append("LENGTH(word) >= ?")
            params.append(min_length)
        
        if max_length is not None:
            conditions.append("LENGTH(word) <= ?")
            params.append(max_length)
        
        sql = "SELECT * FROM domains"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
    
    def get_available(self, min_score: Optional[float] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all available domains, optionally filtered by minimum score."""
        return self.query(available=True, min_score=min_score, limit=limit)
    
    def get_top(self, n: int = 50) -> List[Dict[str, Any]]:
        """Get top N available domains by score."""
        return self.query(available=True, limit=n)
    
    def stats(self) -> Dict[str, Any]:
        """Get statistics about stored results."""
        with sqlite3.connect(self.db_file) as conn:
            total = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
            available = conn.execute("SELECT COUNT(*) FROM domains WHERE available = 1").fetchone()[0]
            unavailable = conn.execute("SELECT COUNT(*) FROM domains WHERE available = 0").fetchone()[0]
            unknown = conn.execute("SELECT COUNT(*) FROM domains WHERE available IS NULL").fetchone()[0]
            
            score_stats = conn.execute("""
                SELECT AVG(total_score), MAX(total_score), MIN(total_score), COUNT(total_score)
                FROM domains WHERE available = 1 AND total_score IS NOT NULL
            """).fetchone()
            
            tld_rows = conn.execute("""
                SELECT tld, COUNT(*) as cnt, SUM(CASE WHEN available = 1 THEN 1 ELSE 0 END) as avail
                FROM domains GROUP BY tld ORDER BY cnt DESC
            """).fetchall()
            
            return {
                "total": total,
                "available": available,
                "unavailable": unavailable,
                "unknown": unknown,
                "avg_score": round(score_stats[0], 1) if score_stats[0] else 0,
                "max_score": round(score_stats[1], 1) if score_stats[1] else 0,
                "min_score": round(score_stats[2], 1) if score_stats[2] else 0,
                "with_scores": score_stats[3] or 0,
                "tlds": {row[0]: {"total": row[1], "available": row[2]} for row in tld_rows}
            }
    
    def export_csv(self, output_file: str, available_only: bool = True):
        """Export results to CSV."""
        import csv
        
        results = self.query(available=True if available_only else None)
        if not results:
            return 0
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        return len(results)
