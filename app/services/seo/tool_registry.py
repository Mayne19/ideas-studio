from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class IntegrationMode(str, Enum):
    KNOWLEDGE_PACK = "knowledge_pack"
    ADAPTER = "adapter"
    VENDOR_SNAPSHOT = "vendor_snapshot"
    INSPIRATION_ONLY = "inspiration_only"
    DO_NOT_INTEGRATE = "do_not_integrate"


@dataclass(frozen=True)
class ExternalSeoTool:
    key: str
    display_name: str
    source_type: str
    upstream_url: str
    audited_commit: str | None
    license_name: str | None
    safe_to_read: bool
    safe_to_execute: bool
    safe_to_vendor: bool
    recommended_mode: IntegrationMode
    intended_uses: Tuple[str, ...]
    warnings: Tuple[str, ...]


EXTERNAL_SEO_TOOLS: tuple[ExternalSeoTool, ...] = (
    ExternalSeoTool(
        key="google_search_central",
        display_name="Google Search Central",
        source_type="official_docs",
        upstream_url="https://developers.google.com/search/",
        audited_commit=None,
        license_name=None,
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.KNOWLEDGE_PACK,
        intended_uses=(
            "official SEO policy baseline",
            "starter guide knowledge pack",
            "content and indexing rules",
        ),
        warnings=(
            "Treat as normative source, not executable code.",
            "Prefer source links over copied text when possible.",
        ),
    ),
    ExternalSeoTool(
        key="google_search_status_dashboard",
        display_name="Google Search Status Dashboard",
        source_type="official_status",
        upstream_url="https://status.search.google.com/",
        audited_commit=None,
        license_name=None,
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.ADAPTER,
        intended_uses=(
            "daily status polling",
            "ranking incident tracking",
            "Google update watch",
        ),
        warnings=(
            "Use a read-only fetcher.",
            "Store source URL and timestamps with every event.",
        ),
    ),
    ExternalSeoTool(
        key="claude_seo_agrici",
        display_name="Claude SEO (AgriciDaniel)",
        source_type="github_repo",
        upstream_url="https://github.com/AgriciDaniel/claude-seo",
        audited_commit="7676024a0200c8aa636d03dc1de136c1cc8d5ffc",
        license_name="MIT",
        safe_to_read=True,
        safe_to_execute=False,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.KNOWLEDGE_PACK,
        intended_uses=(
            "FLOW workflow inspiration",
            "SEO brief and audit checklists",
            "GEO and EEAT prompt patterns",
        ),
        warnings=(
            "Do not execute install/uninstall scripts.",
            "Do not let external scripts write into user config directories.",
        ),
    ),
    ExternalSeoTool(
        key="claude_seo_ivan",
        display_name="Claude SEO (ivankuznetsov)",
        source_type="github_repo",
        upstream_url="https://github.com/ivankuznetsov/claude-seo",
        audited_commit="81284b89275abe14d9ddc048937b5b7e956103d4",
        license_name="MIT",
        safe_to_read=True,
        safe_to_execute=False,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.KNOWLEDGE_PACK,
        intended_uses=(
            "research-write-humanize-fact-check workflow",
            "humanization patterns",
            "editorial process inspiration",
        ),
        warnings=(
            "Do not run SessionStart dependency installers.",
            "Do not adopt the Ruby runtime layer without a separate review.",
        ),
    ),
    ExternalSeoTool(
        key="seo_geo_claude_skills",
        display_name="SEO & GEO Claude Skills",
        source_type="github_repo",
        upstream_url="https://github.com/aaron-he-zhu/seo-geo-claude-skills",
        audited_commit="b69ebc6ab437b5b53f0aac375b00a6b713620a30",
        license_name="Apache-2.0",
        safe_to_read=True,
        safe_to_execute=False,
        safe_to_vendor=True,
        recommended_mode=IntegrationMode.KNOWLEDGE_PACK,
        intended_uses=(
            "CORE-EEAT benchmark inspiration",
            "CITE domain trust benchmark inspiration",
            "SEO/GEO workflow structure",
        ),
        warnings=(
            "Do not reuse hooks or memory-management runtime directly.",
            "Keep Apache notice requirements in mind for any vendor snapshot.",
        ),
    ),
    ExternalSeoTool(
        key="humanizer",
        display_name="Humanizer",
        source_type="github_repo",
        upstream_url="https://github.com/blader/humanizer",
        audited_commit="8b3a17889fbf12bedae20974a3c9f9de746ed754",
        license_name="MIT",
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=True,
        recommended_mode=IntegrationMode.KNOWLEDGE_PACK,
        intended_uses=(
            "AI-writing anti-pattern reference",
            "final humanization pass",
        ),
        warnings=(
            "Use as prompt/checklist guidance, not as autonomous rewriting authority.",
        ),
    ),
    ExternalSeoTool(
        key="semrush_blog",
        display_name="Semrush Blog",
        source_type="commercial_blog",
        upstream_url="https://www.semrush.com/blog/",
        audited_commit=None,
        license_name=None,
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.INSPIRATION_ONLY,
        intended_uses=(
            "trend watching",
            "keyword strategy inspiration",
            "AI search examples",
        ),
        warnings=(
            "Treat as commercial guidance, not as a policy source.",
        ),
    ),
    ExternalSeoTool(
        key="ahrefs_blog",
        display_name="Ahrefs Blog",
        source_type="commercial_blog",
        upstream_url="https://ahrefs.com/blog/",
        audited_commit=None,
        license_name=None,
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.INSPIRATION_ONLY,
        intended_uses=(
            "practical tutorials",
            "SEO examples and studies",
            "keyword and on-page heuristics",
        ),
        warnings=(
            "Treat as a secondary source behind Google official guidance.",
        ),
    ),
    ExternalSeoTool(
        key="neil_patel",
        display_name="Neil Patel",
        source_type="commercial_blog",
        upstream_url="https://neilpatel.com/blog/",
        audited_commit=None,
        license_name=None,
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.INSPIRATION_ONLY,
        intended_uses=(
            "headline and marketing-angle inspiration",
        ),
        warnings=(
            "Use carefully and verify against stronger sources.",
        ),
    ),
    ExternalSeoTool(
        key="nelly_kempf",
        display_name="Nelly Kempf",
        source_type="expert_site",
        upstream_url="https://www.nellykempf.com/",
        audited_commit=None,
        license_name=None,
        safe_to_read=True,
        safe_to_execute=True,
        safe_to_vendor=False,
        recommended_mode=IntegrationMode.INSPIRATION_ONLY,
        intended_uses=(
            "brand SEO framing",
            "editorial positioning inspiration",
            "SEO plus conversion thinking",
        ),
        warnings=(
            "Use as expert inspiration, not as a canonical rules source.",
        ),
    ),
)

