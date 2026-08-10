from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from helpers.get_sensor_hourly_count import SCAPIRecord, get_sc_data
from models.raw_sensor_count import (
    RawSensorCount,
    SCIngestionRun
)
from models.sensor_hourly_count import SensorHourlyCount


# Recalculate the last N hours so late-arriving API records
# can be incorporated.
REPROCESS_HOURS = 2
MELBOURNE = ZoneInfo("Australia/Melbourne")


# UTILITY FUNCTIONS
def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware and represented in UTC.
    """

    if dt.tzinfo is None:
        raise ValueError(
            f"Datetime must be timezone-aware: {dt}"
        )

    return dt.astimezone(timezone.utc)

def to_melbourne(dt: datetime) -> datetime:
    """
    Convert an aware datetime to Melbourne time.
    """

    return dt.astimezone(MELBOURNE)


def melbourne_hour_start(dt: datetime) -> datetime:
    """
    Return the start of the Melbourne local hour.
    Example:
        2026-08-10 10:37 +10:00 -> 2026-08-10 10:00 +10:00
    """

    local = to_melbourne(dt)

    return local.replace(
        minute=0,
        second=0,
        microsecond=0,
    )

def save_raw_data(
    session: Session,
    records: list[SCAPIRecord],
) -> None:
    # get current time
    retrieved_at = datetime.now(timezone.utc)

    for record in records:
        # Check whether we already have this API measurement.
        existing = session.exec(
            select(RawSensorCount)
            .where(
                RawSensorCount.location_id == record.location_id,
                RawSensorCount.sensing_datetime == record.sensing_datetime,
            )
        ).first()

        if existing:
            # If the API can correct historical values, update the existing record.
            existing.direction_1 = record.direction_1
            existing.direction_2 = record.direction_2
            existing.total_of_directions = record.total_of_directions
            existing.retrieved_at = retrieved_at
        else:
            dt = ensure_utc(record.sensing_datetime)
            session.add(
                RawSensorCount(
                    location_id=record.location_id,
                    sensing_datetime=record.sensing_datetime,
                    sensing_date=record.sensing_date,
                    sensing_time=record.sensing_time,
                    direction_1=record.direction_1,
                    direction_2=record.direction_2,
                    total_of_directions=record.total_of_directions,
                    retrieved_at=dt
                )
            )

    session.commit()

def get_latest_timestamp(
    session: Session,
) -> datetime | None:

    return session.exec(
        select(func.max(RawSensorCount.sensing_datetime))
    ).one()

def get_latest_melbourne_hour(
    session: Session,
) -> datetime | None:

    latest = get_latest_timestamp(session)

    if latest is None:
        return None

    return melbourne_hour_start(latest)

def upsert_hourly_data(
    session: Session,
    location_id: str,
    local_date,
    local_hour: int,
    direction_1: int | None,
    direction_2: int | None,
    total_of_directions: int | None
) -> None:
    """
    Insert or update an hourly aggregate.
    Unique key: sensor_id + sc_date + sc_hour
    """

    added_at = datetime.now(timezone.utc)
    statement = insert(SensorHourlyCount).values(
        sensor_id=location_id,
        sc_date=local_date,
        sc_hour=local_hour,
        sc_dir1=direction_1,
        sc_dir2=direction_2,
        sc_totaldirs=total_of_directions,
        sc_addedat=added_at
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_sc",
        set_={
            "sc_dir1": statement.excluded.sc_dir1,
            "sc_dir2": statement.excluded.sc_dir2,
            "sc_totaldirs": statement.excluded.sc_totaldirs,
            "sc_addedat": statement.excluded.sc_addedat,
        }
    )

    session.exec(statement)



# Aggregate one Melbourne hour

def aggregate_hour(
    session: Session,
    hour_start_local: datetime,
) -> None:
    """
    Aggregate one Melbourne local hour.
    Example:
        hour_start_local = 2026-08-10 10:00 +10:00
    Query range:
        2026-08-10 00:00 UTC -> 2026-08-10 01:00 UTC
    The result is stored as:
        date = 2026-08-10
        hour = 10
    """

    # Make sure the hour is represented in Melbourne.
    hour_start_local = hour_start_local.astimezone(MELBOURNE)
    hour_end_local = (hour_start_local + timedelta(hours=1))

    # Convert the Melbourne boundaries to UTC.
    start_utc = hour_start_local.astimezone(timezone.utc)
    end_utc = hour_end_local.astimezone(timezone.utc)

    # Aggregate directly in PostgreSQL.
    rows = session.exec(
        select(
            RawSensorCount.location_id,
            func.sum(RawSensorCount.direction_1).label("sc_dir1"),
            func.sum(RawSensorCount.direction_2).label("sc_dir2"),
            func.sum(RawSensorCount.total_of_directions).label("sc_totaldirs"),
        )
        .where(
            RawSensorCount.sensing_datetime >= start_utc,
            RawSensorCount.sensing_datetime < end_utc,
        )
        .group_by(
            RawSensorCount.location_id
        )
    ).all()

    # The final table stores Melbourne local
    # date + hour.
    local_date = hour_start_local.date()
    local_hour = hour_start_local.hour

    for row in rows:
        upsert_hourly_data(
            session=session,
            location_id=row.location_id,
            local_date=local_date,
            local_hour=local_hour,
            direction_1=row.sc_dir1,
            direction_2=row.sc_dir2,
            total_of_directions=row.sc_totaldirs
        )

    session.commit()



# Process completed hours

def process_completed_hours(
    session: Session,
    latest_hour: datetime,
) -> None:
    """
    Process all hours that are known to be complete.
    If the latest API hour is 11:00:
        11:00 = potentially incomplete
        10:00 = complete
    Therefore we process through 10:00.
    """

    # Latest hour may still be incomplete.
    completed_until = latest_hour - timedelta(hours=1)

    # Get ingestion state.
    state = session.exec(
        select(SCIngestionRun)
    ).first()

    # Create state on first run.
    if state is None:
        state = SCIngestionRun(
            last_processed_hour=None,
        )
        session.add(state)
        session.flush()

    # First run
    if state.last_processed_hour is None:
        earliest_timestamp = session.exec(
            select(func.min(RawSensorCount.sensing_datetime))
        ).one()

        if earliest_timestamp is None:
            return

        current = melbourne_hour_start(earliest_timestamp)

    # Subsequent runs
    else:
        # Normally continue from the hour after the watermark.
        current = state.last_processed_hour + timedelta(hours=1)

        # Reprocess recent completed hours.
        # Example:
        # completed_until = 12:00
        # REPROCESS_HOURS = 2
        # reprocess from 11:00.
        reprocess_start = completed_until - timedelta(hours=REPROCESS_HOURS - 1)

        current = min(current, reprocess_start)

    # Nothing new to process.
    if current > completed_until:
        return

    # Aggregate each completed hour
    while current <= completed_until:
        aggregate_hour(
            session=session,
            hour_start_local=current,
        )
        current += timedelta(hours=1)

    # Advance the watermark.
    state.last_processed_hour = completed_until

    session.add(state)
    session.commit()


# Main ingestion job
async def run_sc_ingestion(
    session: Session
) -> dict:
    """
    Complete ingestion process:
        1. Call external API
        2. Save raw records
        3. Find latest Melbourne hour
        4. Aggregate completed hours
        5. Update ingestion state
    """

    print("Starting API ingestion...")

    # 1. Retrieve API data
    records = await get_sc_data()

    if not records:
        print("API returned no data.")

        return {
            "status": "no_data",
            "records": 0,
        }

    print(
        f"Retrieved {len(records)} API records."
    )

    # 2. Save raw records.
    save_raw_data(
        session=session,
        records=records,
    )

    # 3. Find latest Melbourne hour
    latest_hour = get_latest_melbourne_hour(session)

    if latest_hour is None:
        return {
            "status": "no_data",
            "records": len(records),
        }

    print(f"Latest Melbourne hour: {latest_hour}")

    # 4. Aggregate completed hours
    process_completed_hours(
        session=session,
        latest_hour=latest_hour,
    )

    # 5. Update ingestion state
    state = session.exec(select(SCIngestionRun)).first()

    if state:
        state.last_successful_retrieval = datetime.now(timezone.utc)
        session.add(state)
        session.commit()

    print("Ingestion completed.")

    return {
        "status": "success",
        "records": len(records),
        "latest_melbourne_hour": latest_hour.isoformat(),
    }