import logging
import time
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database import SessionLocal
from config import settings
from market_data.storage.models import MarketCandle
from market_data.normalizers.binance import BinanceNormalizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BinanceIngester")

class BinanceIngester:
    BASE_URL = "https://api.binance.com/api/v3/klines"
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.normalizer = BinanceNormalizer()
        
    def fetch_klines_with_retry(self, symbol: str, interval: str, start_time_ms: int, end_time_ms: int = None, limit: int = 1000, max_retries: int = 5):
        """Fetch a single page of klines from Binance with exponential backoff retries."""
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time_ms,
            "limit": limit
        }
        if end_time_ms:
            params["endTime"] = end_time_ms
            
        for attempt in range(max_retries):
            try:
                response = httpx.get(self.BASE_URL, params=params, timeout=15.0)
                
                # Handle rate limits
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logger.warning(f"Rate limited by Binance. Sleeping for {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching data for {symbol} (Attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2 ** attempt) # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error (Attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)
                
        logger.error(f"Failed to fetch {symbol} after {max_retries} attempts.")
        return []

    def validate_ohlc(self, records: list[dict]) -> list[dict]:
        """Ensure OHLC consistency and reject malformed records safely."""
        valid_records = []
        for r in records:
            # Consistency checks
            if not (r['low'] <= r['open'] <= r['high']) or not (r['low'] <= r['close'] <= r['high']):
                logger.warning(f"Malformed OHLC data skipped for {r['symbol']} at {r['timestamp']}: O:{r['open']} H:{r['high']} L:{r['low']} C:{r['close']}")
                continue
            if r['volume'] < 0:
                logger.warning(f"Negative volume skipped for {r['symbol']} at {r['timestamp']}")
                continue
                
            valid_records.append(r)
        return valid_records

    def store_candles(self, records: list[dict]):
        """Bulk insert candles, ignoring duplicates safely."""
        if not records:
            return 0
            
        try:
            # Try PostgreSQL-specific upsert
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(MarketCandle).values(records)
            on_conflict_stmt = stmt.on_conflict_do_nothing(
                index_elements=['symbol', 'timeframe', 'timestamp', 'source']
            )
            result = self.db.execute(on_conflict_stmt)
            self.db.commit()
            return result.rowcount
        except Exception:
            self.db.rollback()
            try:
                # Fallback to SQLite or generic bulk insert
                # On SQLite, we can use prefix_with("OR IGNORE")
                from sqlalchemy import insert
                stmt = insert(MarketCandle).values(records)
                if self.db.bind.dialect.name == 'sqlite':
                    stmt = stmt.prefix_with("OR IGNORE")
                
                result = self.db.execute(stmt)
                self.db.commit()
                return result.rowcount
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to store candles: {e}")
                return 0

    def ingest_historical(self, symbol: str, interval: str, start_date: datetime, end_date: datetime):
        """Fetch and store historical data sequentially handling pagination."""
        logger.info(f"[{symbol}][{interval}] Starting long-range ingestion: {start_date.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}")
        
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        batch_size = settings.INGEST_BATCH_SIZE
        
        total_inserted = 0
        current_start = start_ms
        
        while current_start < end_ms:
            # Display progress tracking
            current_start_dt = datetime.fromtimestamp(current_start/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            # Estimate end of this batch for logging
            estimated_end_dt = datetime.fromtimestamp(min(end_ms, current_start + (batch_size * 3600 * 1000 if interval == '1h' else batch_size * 60 * 1000)) / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            logger.info(f"[{symbol}][{interval}] Fetching candles: {current_start_dt} -> {estimated_end_dt}")
            
            raw_data = self.fetch_klines_with_retry(symbol, interval, current_start, end_ms, limit=batch_size)
            
            if not raw_data:
                logger.warning(f"[{symbol}][{interval}] No data returned at {current_start_dt}. Stopping pagination.")
                break
                
            normalized_candles = self.normalizer.normalize(raw_data, symbol, interval)
            records = [candle.model_dump() for candle in normalized_candles]
            
            # Validate numeric consistency
            valid_records = self.validate_ohlc(records)
            
            # Efficient database write
            inserted_count = self.store_candles(valid_records)
            total_inserted += inserted_count
            
            # Safely determine the next start time to avoid infinite loops on exact same timestamps
            last_candle_time = raw_data[-1][0]
            if last_candle_time <= current_start and len(raw_data) == 1:
                # API returned the exact same candle, force step forward to break loop
                current_start += 1000
            else:
                current_start = last_candle_time + 1
            
            # Prevent rate limits
            time.sleep(0.1)
            
            # If we received less than the limit, we hit the end of available historical data
            if len(raw_data) < batch_size:
                break
                
        logger.info(f"[{symbol}][{interval}] Ingestion complete. Total new candles safely inserted: {total_inserted}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        ingester = BinanceIngester(db)
        
        # Load from config
        try:
            start = datetime.strptime(settings.INGEST_START_DATE, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error("Invalid INGEST_START_DATE format. Using 2017-01-01.")
            start = datetime(2017, 1, 1, tzinfo=timezone.utc)
            
        end = datetime.now(timezone.utc)
        
        symbols = [s.strip() for s in settings.INGEST_SYMBOLS.split(",")]
        timeframes = [t.strip() for t in settings.INGEST_TIMEFRAMES.split(",")]
        
        for sym in symbols:
            for tf in timeframes:
                ingester.ingest_historical(sym, tf, start, end)
                
    except Exception as e:
        logger.error(f"Critical ingestion failure: {e}")
    finally:
        db.close()
