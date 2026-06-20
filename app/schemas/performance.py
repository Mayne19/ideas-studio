from typing import Optional
from typing import Literal
from pydantic import BaseModel


class DayViews(BaseModel):
    date: str
    views: int


class ChannelDayViews(BaseModel):
    date: str
    direct: int
    organic: int
    social: int
    referral: int


class TopPage(BaseModel):
    path: str
    views: int


class ReferrerStats(BaseModel):
    referrer: str
    views: int


class CountryStats(BaseModel):
    country: str
    views: int


class DeviceStats(BaseModel):
    device: str
    views: int


class ProjectTrafficSummary(BaseModel):
    tracking_status: Literal["not_configured", "configured_no_data", "connected_with_data", "error"]
    total_views: int
    unique_pages: int
    top_pages: list[TopPage]
    referrers: list[ReferrerStats]
    countries: list[CountryStats]
    devices: list[DeviceStats]
    trend_by_day: list[DayViews]
    channel_trend_by_day: list[ChannelDayViews]
    period: str


class ArticlePerformance(BaseModel):
    article_id: str
    views: int
    referrers: list[ReferrerStats]
    countries: list[CountryStats]
    daily_views: list[DayViews]
    last_seen_at: Optional[str]
    period: str


class ArticlePerformanceBrief(BaseModel):
    article_id: str
    title: str
    slug: str
    views: int
    variation: Optional[float] = None
    seo_score: Optional[float]
    published_at: Optional[str]
