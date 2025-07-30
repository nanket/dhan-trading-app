"""Open Interest change tracking and analysis."""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import asdict

from ..api.models import OIChangeData
from ..config import config

import logging

logger = logging.getLogger(__name__)


class OIChangeTracker:
    """Tracks and calculates open interest changes for option contracts."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize OI change tracker.

        Args:
            db_path: Path to SQLite database file. If None, uses default path.
        """
        # Use project data directory instead of home directory
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            self.db_path = data_dir / "oi_tracker.db"
        else:
            self.db_path = Path(db_path)

        self.lock = threading.Lock()

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        logger.info(f"OI Change Tracker initialized with database: {self.db_path}")
    
    def _init_database(self):
        """Initialize SQLite database for OI tracking."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oi_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    underlying_scrip INTEGER NOT NULL,
                    expiry TEXT NOT NULL,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL,  -- 'CE' or 'PE'
                    oi INTEGER NOT NULL,
                    volume INTEGER NOT NULL,
                    ltp REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    session_date DATE NOT NULL,
                    UNIQUE(underlying_scrip, expiry, strike, option_type, session_date)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_oi_snapshots_lookup 
                ON oi_snapshots(underlying_scrip, expiry, strike, option_type, session_date)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_oi_snapshots_timestamp 
                ON oi_snapshots(timestamp)
            """)
            
            conn.commit()
    
    def store_oi_snapshot(
        self,
        underlying_scrip: int,
        expiry: str,
        strike: float,
        option_type: str,
        oi: int,
        volume: int,
        ltp: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Store OI snapshot for later comparison.
        
        Args:
            underlying_scrip: Security ID of underlying
            expiry: Option expiry date
            strike: Strike price
            option_type: 'CE' or 'PE'
            oi: Current open interest
            volume: Current volume
            ltp: Last traded price
            timestamp: Snapshot timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        session_date = timestamp.date()
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO oi_snapshots 
                        (underlying_scrip, expiry, strike, option_type, oi, volume, ltp, timestamp, session_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (underlying_scrip, expiry, strike, option_type, oi, volume, ltp, timestamp, session_date))
                    
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Error storing OI snapshot: {e}")
    
    def get_oi_change(
        self,
        underlying_scrip: int,
        expiry: str,
        strike: float,
        option_type: str,
        current_oi: int,
        comparison_date: Optional[datetime] = None
    ) -> Optional[OIChangeData]:
        """Calculate OI change compared to previous session.
        
        Args:
            underlying_scrip: Security ID of underlying
            expiry: Option expiry date
            strike: Strike price
            option_type: 'CE' or 'PE'
            current_oi: Current open interest
            comparison_date: Date to compare against (defaults to previous trading day)
            
        Returns:
            OI change data or None if no previous data available
        """
        if comparison_date is None:
            # Get previous trading day (assuming weekdays only for now)
            today = datetime.now().date()
            comparison_date = today - timedelta(days=1)
            
            # Skip weekends (simple logic - could be enhanced for holidays)
            while comparison_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                comparison_date -= timedelta(days=1)
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        SELECT oi, timestamp FROM oi_snapshots 
                        WHERE underlying_scrip = ? AND expiry = ? AND strike = ? 
                        AND option_type = ? AND session_date = ?
                        ORDER BY timestamp DESC LIMIT 1
                    """, (underlying_scrip, expiry, strike, option_type, comparison_date))
                    
                    row = cursor.fetchone()
                    
                    if row is None:
                        return None
                    
                    previous_oi, timestamp_str = row
                    
                    # Calculate changes
                    absolute_change = current_oi - previous_oi
                    percentage_change = (absolute_change / previous_oi * 100) if previous_oi > 0 else 0.0
                    
                    return OIChangeData(
                        absolute_change=absolute_change,
                        percentage_change=percentage_change,
                        previous_oi=previous_oi,
                        current_oi=current_oi,
                        timestamp=datetime.now()
                    )
                    
            except Exception as e:
                logger.error(f"Error calculating OI change: {e}")
                return None
    
    def store_option_chain_snapshot(
        self,
        underlying_scrip: int,
        expiry: str,
        option_chain_data: Dict,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Store complete option chain snapshot.
        
        Args:
            underlying_scrip: Security ID of underlying
            expiry: Option expiry date
            option_chain_data: Option chain data from API
            timestamp: Snapshot timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Extract and store OI data for each strike
        for strike_price, strike_data in option_chain_data.get("strikes", {}).items():
            strike = float(strike_price)
            
            # Store CE data
            if "ce" in strike_data and strike_data["ce"]:
                ce_data = strike_data["ce"]
                self.store_oi_snapshot(
                    underlying_scrip=underlying_scrip,
                    expiry=expiry,
                    strike=strike,
                    option_type="CE",
                    oi=ce_data.get("oi", 0),
                    volume=ce_data.get("volume", 0),
                    ltp=ce_data.get("last_price", 0.0),
                    timestamp=timestamp
                )
            
            # Store PE data
            if "pe" in strike_data and strike_data["pe"]:
                pe_data = strike_data["pe"]
                self.store_oi_snapshot(
                    underlying_scrip=underlying_scrip,
                    expiry=expiry,
                    strike=strike,
                    option_type="PE",
                    oi=pe_data.get("oi", 0),
                    volume=pe_data.get("volume", 0),
                    ltp=pe_data.get("last_price", 0.0),
                    timestamp=timestamp
                )
    
    def get_top_oi_changes(
        self,
        underlying_scrip: int,
        expiry: str,
        limit: int = 10,
        change_type: str = "absolute"  # "absolute" or "percentage"
    ) -> List[Dict]:
        """Get top OI changes for analysis.
        
        Args:
            underlying_scrip: Security ID of underlying
            expiry: Option expiry date
            limit: Number of top changes to return
            change_type: Type of change to sort by
            
        Returns:
            List of top OI changes with strike and change data
        """
        # This would require current option chain data to calculate changes
        # Implementation would fetch current data and calculate changes for all strikes
        # For now, returning empty list as placeholder
        return []
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old OI snapshot data.
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        DELETE FROM oi_snapshots WHERE timestamp < ?
                    """, (cutoff_date,))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    logger.info(f"Cleaned up {deleted_count} old OI snapshot records")
                    
            except Exception as e:
                logger.error(f"Error cleaning up old data: {e}")
