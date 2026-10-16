"""Réglages des images d'illustration (ai.illustration_settings).

Trois modes, choisis depuis Paramètres → Services externes :
- "ai"       : illustrations générées (OpenRouter, clé des Providers IA) dans
               un style visuel de marque constant ;
- "unsplash" : photos Unsplash + images officielles de marques (historique) ;
- "none"     : aucune image.

Résolution : ligne projet, puis ligne globale, puis défauts du code (mode
"unsplash" : comportement historique conservé tant que rien n'est choisi).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app.services.providers.image_generation_provider import DEFAULT_IMAGE_MODEL, IMAGE_MODELS

MODES: dict[str, str] = {
    "ai": "Générées par IA",
    "unsplash": "Photos Unsplash",
    "none": "Aucune",
}
DEFAULT_MODE = "unsplash"

# Directives envoyées au modèle d'image (en anglais : meilleure adhérence).
STYLE_PRESETS: dict[str, dict[str, str]] = {
    "flat_editorial": {
        "label": "Illustration éditoriale plate",
        "directive": (
            "flat editorial illustration, clean vector shapes, subtle grain texture, "
            "generous negative space, calm and serious magazine style"
        ),
    },
    "isometric": {
        "label": "Isométrique",
        "directive": (
            "isometric 3D illustration, soft shading, precise geometry, "
            "clean minimal scene, professional tech editorial style"
        ),
    },
    "line_sketch": {
        "label": "Croquis au trait",
        "directive": (
            "hand-drawn ink line sketch, fine pen strokes, light color wash accents, "
            "elegant editorial drawing on off-white paper"
        ),
    },
    "abstract_patterns": {
        "label": "Motifs abstraits",
        "directive": (
            "abstract geometric pattern composition, layered shapes and rhythms "
            "evoking the concept, modern minimal editorial artwork"
        ),
    },
    "custom": {"label": "Style personnalisé", "directive": ""},
}
DEFAULT_STYLE = "flat_editorial"

DEFAULT_CONFIG: dict = {
    "model": DEFAULT_IMAGE_MODEL,
    "style_preset": DEFAULT_STYLE,
    "custom_style": "",
    "primary_color": "#1F3A5F",
    "secondary_color": "#E07A5F",
    "max_images": 3,
}
MAX_IMAGES_LIMIT = 6
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

NO_TEXT_RULE = (
    "Absolutely no text, no letters, no numbers, no words, no captions, "
    "no logos, no brand marks, no watermarks, no signatures, no user interface text."
)


class IllustrationSettingsError(ValueError):
    """Réglage invalide (mode, couleur, modèle...)."""


@dataclass
class IllustrationConfig:
    mode: str = DEFAULT_MODE
    model: str = DEFAULT_IMAGE_MODEL
    style_preset: str = DEFAULT_STYLE
    custom_style: str = ""
    primary_color: str = DEFAULT_CONFIG["primary_color"]
    secondary_color: str = DEFAULT_CONFIG["secondary_color"]
    max_images: int = DEFAULT_CONFIG["max_images"]
    # "project" | "global" | "default"
    source: str = "default"

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_config(config: dict | None) -> dict:
    """Valide et complète la config (valeurs inconnues ignorées, défauts)."""
    raw = dict(config or {})
    out = dict(DEFAULT_CONFIG)

    model = str(raw.get("model") or "").strip()
    if model:
        if model not in IMAGE_MODELS:
            raise IllustrationSettingsError(f"Modèle d'image '{model}' non supporté")
        out["model"] = model

    preset = str(raw.get("style_preset") or "").strip()
    if preset:
        if preset not in STYLE_PRESETS:
            raise IllustrationSettingsError(f"Style '{preset}' inconnu")
        out["style_preset"] = preset

    out["custom_style"] = str(raw.get("custom_style") or "").strip()[:500]
    if out["style_preset"] == "custom" and not out["custom_style"]:
        raise IllustrationSettingsError("Décrivez le style personnalisé")

    for key in ("primary_color", "secondary_color"):
        value = str(raw.get(key) or "").strip()
        if value:
            if not _HEX_RE.match(value):
                raise IllustrationSettingsError(f"Couleur invalide pour {key} (format #RRGGBB attendu)")
            out[key] = value.upper()

    if raw.get("max_images") is not None and raw.get("max_images") != "":
        try:
            max_images = int(raw["max_images"])
        except (TypeError, ValueError) as exc:
            raise IllustrationSettingsError("Nombre d'images invalide") from exc
        out["max_images"] = max(0, min(MAX_IMAGES_LIMIT, max_images))
    return out


def config_from_row(row) -> IllustrationConfig:
    try:
        cfg = normalize_config(row.config)
    except IllustrationSettingsError:
        cfg = dict(DEFAULT_CONFIG)
    mode = row.mode if row.mode in MODES else DEFAULT_MODE
    return IllustrationConfig(mode=mode, source="project" if row.project_id else "global", **cfg)


def find_row(db, project_id: str | None):
    from sqlalchemy import select

    from app.models.ai import IllustrationSettings

    query = select(IllustrationSettings)
    if project_id:
        query = query.where(IllustrationSettings.project_id == project_id)
    else:
        query = query.where(IllustrationSettings.project_id.is_(None))
    return db.execute(query.limit(1)).scalar_one_or_none()


def resolve_config(db, project_id: str | None) -> IllustrationConfig:
    """Config effective : projet, puis globale, puis défauts. Ne lève jamais
    (une table absente ou une erreur de lecture retombe sur les défauts)."""
    if db is None:
        return IllustrationConfig()
    try:
        for scope in ([project_id, None] if project_id else [None]):
            row = find_row(db, scope)
            if row is not None:
                return config_from_row(row)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    return IllustrationConfig()


def upsert_config(db, project_id: str | None, mode: str, config: dict | None):
    from app.models.ai import IllustrationSettings

    if mode not in MODES:
        raise IllustrationSettingsError(f"Mode '{mode}' inconnu")
    normalized = normalize_config(config)
    row = find_row(db, project_id)
    if row is None:
        row = IllustrationSettings(project_id=project_id)
        db.add(row)
    row.mode = mode
    row.config = normalized
    db.commit()
    db.refresh(row)
    return row


# ── Prompt d'image ─────────────────────────────────────────────────────────


def style_directive(cfg: IllustrationConfig) -> str:
    if cfg.style_preset == "custom":
        return cfg.custom_style.strip() or STYLE_PRESETS[DEFAULT_STYLE]["directive"]
    preset = STYLE_PRESETS.get(cfg.style_preset) or STYLE_PRESETS[DEFAULT_STYLE]
    return preset["directive"]


def compose_image_prompt(scene: str, cfg: IllustrationConfig) -> str:
    """Prompt final envoyé au modèle d'image : scène (propre à la section) +
    style de marque constant + palette + interdiction de tout texte."""
    scene = re.sub(r"\s+", " ", (scene or "")).strip().rstrip(".")
    return (
        f"{scene}. "
        f"Style: {style_directive(cfg)}. "
        f"Restricted color palette built around {cfg.primary_color} (primary) and "
        f"{cfg.secondary_color} (accent) with neutral off-white and dark tones; "
        "consistent with a series of illustrations for the same publication. "
        "Wide 16:9 landscape composition, single clear focal point, no photorealism. "
        f"{NO_TEXT_RULE}"
    )
