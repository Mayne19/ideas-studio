"""Résolution des providers IA depuis ai.providers/ai.provider_credentials/
ai.agent_bindings — remplace AIProviderConfig (voir REPRENDRE-LA-MAIN.md §5,
'AiProviderConfig' -> 'ai.providers + ai.provider_credentials'). Le binding
n'a pas de colonne is_default : le classement par priority (asc) EST le
mécanisme de défaut, voir la doc de ai.agent_bindings dans 01-schema.sql."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import AgentBinding, Provider, ProviderCredential


@dataclass
class ResolvedProviderConfig:
    """Vue plate consommée par build_provider_from_config — mêmes noms de
    champs que l'ancien AIProviderConfig pour ne pas devoir réécrire cette
    fonction ni les classes *LLMProvider en aval."""

    id: str
    provider: str
    model: str | None
    base_url: str | None
    api_key_encrypted: str | None


def _to_config(provider_row: Provider, credential: ProviderCredential | None, model: str | None, binding_id: str) -> ResolvedProviderConfig:
    return ResolvedProviderConfig(
        id=binding_id,
        provider=provider_row.code,
        model=model,
        base_url=provider_row.base_url,
        api_key_encrypted=credential.secret_ref if credential else None,
    )


def _credential_for(db: Session, provider_id: str, project_id: str | None) -> ProviderCredential | None:
    """Credential projet si présent, sinon credential global (project_id NULL)."""
    if project_id is not None:
        cred = db.execute(
            select(ProviderCredential).where(
                ProviderCredential.provider_id == provider_id,
                ProviderCredential.project_id == project_id,
            )
        ).scalar_one_or_none()
        if cred is not None:
            return cred
    return db.execute(
        select(ProviderCredential).where(
            ProviderCredential.provider_id == provider_id,
            ProviderCredential.project_id.is_(None),
        )
    ).scalar_one_or_none()


def resolve_binding_for_agent(db: Session, agent_row_id: str, project_id: str | None) -> ResolvedProviderConfig | None:
    """Ligne projet sinon ligne globale, priority croissante = préférence
    décroissante (voir docstring de AgentBinding dans app/models/ai.py)."""
    binding = None
    if project_id is not None:
        binding = db.execute(
            select(AgentBinding)
            .where(
                AgentBinding.agent_id == agent_row_id,
                AgentBinding.project_id == project_id,
                AgentBinding.is_enabled.is_(True),
            )
            .order_by(AgentBinding.priority.asc())
            .limit(1)
        ).scalar_one_or_none()
    if binding is None:
        binding = db.execute(
            select(AgentBinding)
            .where(
                AgentBinding.agent_id == agent_row_id,
                AgentBinding.project_id.is_(None),
                AgentBinding.is_enabled.is_(True),
            )
            .order_by(AgentBinding.priority.asc())
            .limit(1)
        ).scalar_one_or_none()
    if binding is None:
        return None

    provider_row = db.get(Provider, binding.provider_id)
    if provider_row is None or not provider_row.is_enabled:
        return None

    credential = _credential_for(db, provider_row.id, project_id)
    return _to_config(provider_row, credential, binding.model, binding.id)


def resolve_default_provider(db: Session, project_id: str | None) -> ResolvedProviderConfig | None:
    """Provider par défaut : premier ai.provider_credentials disponible pour
    le projet (puis global), en préférant le provider le mieux classé parmi
    les bindings existants s'il y en a, sinon la première credential trouvée."""
    if project_id is not None:
        cred = db.execute(
            select(ProviderCredential).where(ProviderCredential.project_id == project_id)
        ).scalars().first()
        if cred is not None:
            provider_row = db.get(Provider, cred.provider_id)
            if provider_row is not None and provider_row.is_enabled:
                return _to_config(provider_row, cred, None, cred.id)

    cred = db.execute(
        select(ProviderCredential).where(ProviderCredential.project_id.is_(None))
    ).scalars().first()
    if cred is not None:
        provider_row = db.get(Provider, cred.provider_id)
        if provider_row is not None and provider_row.is_enabled:
            return _to_config(provider_row, cred, None, cred.id)
    return None
