"""한국 시간(KST, UTC+9) 기준 now/today. 서버가 UTC 환경(Railway 등)이어도 동일 동작.
meal_logs.created_at은 한국 시간(naive)으로 저장, API 응답은 KST 문자열로 통일."""
from datetime import datetime, timezone, timedelta, date, time

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
    """한국 기준 오늘 00:00 ~ 내일 00:00을 UTC naive datetime으로. (레거시: created_at이 UTC일 때 필터용)"""
    today = kst_today()
    start_kst = datetime.combine(today, time.min).replace(tzinfo=KST)
    end_kst = datetime.combine(today, time.max).replace(tzinfo=KST) + timedelta(seconds=1)
    start_utc = start_kst.astimezone(UTC).replace(tzinfo=None)
    end_utc = end_kst.astimezone(UTC).replace(tzinfo=None)
    return start_utc, end_utc


def kst_date_range_naive():
    """한국 기준 오늘 00:00 ~ 내일 00:00을 naive datetime으로. created_at(KST naive) 필터용."""
    today = kst_today()
    start_naive = datetime.combine(today, time.min)
    end_naive = datetime.combine(today + timedelta(days=1), time.min)
    return start_naive, end_naive


def kst_date_range_to_utc_naive(start_date: date, end_date: date):
    """한국 기준 날짜 구간을 UTC naive로. (레거시: created_at이 UTC일 때 필터용)"""
    start_kst = datetime.combine(start_date, time.min).replace(tzinfo=KST)
    end_kst = datetime.combine(end_date, time.max).replace(tzinfo=KST) + timedelta(seconds=1)
    start_utc = start_kst.astimezone(UTC).replace(tzinfo=None)
    end_utc = end_kst.astimezone(UTC).replace(tzinfo=None)
    return start_utc, end_utc


def kst_date_range_to_naive(start_date: date, end_date: date):
    """한국 기준 날짜 구간 [start_date 00:00, end_date 다음날 00:00)을 naive datetime으로. created_at(KST naive) 필터용."""
    start_naive = datetime.combine(start_date, time.min)
    end_naive = datetime.combine(end_date + timedelta(days=1), time.min)
    return start_naive, end_naive


def utc_to_kst_str(dt: datetime | None) -> str | None:
    """DB에서 읽은 created_at을 KST 기준 문자열로. naive면 KST로 간주하고 그대로 포맷, aware면 KST로 변환 후 포맷."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
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
