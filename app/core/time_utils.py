"""한국 시간(KST, UTC+9) 기준 now/today. 서버가 UTC 환경(Railway 등)이어도 동일 동작.
저장은 UTC, API 응답은 KST 문자열로 통일."""
from datetime import datetime, timezone, timedelta, date

KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def utc_now():
    """UTC 현재 시각 (저장용)."""
    return datetime.now(UTC)


def kst_now():
    """한국 현재 시각 (timezone-aware)."""
    return datetime.now(KST)


def kst_today():
    """한국 기준 오늘 날짜."""
    return kst_now().date()


def kst_date_range_utc_naive():
    """한국 기준 오늘 00:00 ~ 내일 00:00을 UTC naive datetime으로. DB created_at(UTC) 필터용."""
    from datetime import time as dt_time
    today = kst_today()
    start_kst = datetime.combine(today, dt_time.min).replace(tzinfo=KST)
    end_kst = datetime.combine(today, dt_time.max).replace(tzinfo=KST) + timedelta(seconds=1)
    start_utc = start_kst.astimezone(UTC).replace(tzinfo=None)
    end_utc = end_kst.astimezone(UTC).replace(tzinfo=None)
    return start_utc, end_utc


def kst_date_range_to_utc_naive(start_date: date, end_date: date):
    """한국 기준 날짜 구간 [start_date 00:00 KST, end_date 다음날 00:00 KST)을 UTC naive로. 원시데이터 조회 필터용."""
    from datetime import time as dt_time
    start_kst = datetime.combine(start_date, dt_time.min).replace(tzinfo=KST)
    # end_date 당일 23:59:59.999 KST 다음 초 = end_date+1 00:00:00 KST
    end_kst = datetime.combine(end_date, dt_time.max).replace(tzinfo=KST) + timedelta(seconds=1)
    start_utc = start_kst.astimezone(UTC).replace(tzinfo=None)
    end_utc = end_kst.astimezone(UTC).replace(tzinfo=None)
    return start_utc, end_utc


def utc_to_kst_str(dt: datetime | None) -> str | None:
    """DB 등에서 읽은 datetime(naive=UTC 또는 aware)을 KST 기준 문자열로. 응답용."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(KST).strftime("%Y-%m-%dT%H:%M:%S")


def parse_created_at_kst_to_utc(value: datetime | str | None) -> datetime | None:
    """클라이언트가 보낸 created_at(한국 시간 의미)을 UTC datetime으로. 저장용."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=KST)
        return value.astimezone(UTC)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00") if "Z" in value else value.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt.astimezone(UTC)
        except (ValueError, TypeError):
            return None
    return None
