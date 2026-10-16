import copy

from app.services.providers.openai_provider import OpenAILLMProvider


class OpenRouterLLMProvider(OpenAILLMProvider):
    provider_name: str = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek/deepseek-v4-flash:free",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 180,
        max_retries: int = 3,
        writer_model: str | None = None,
        planner_model: str | None = None,
        proofreader_model: str | None = None,
        fallback_model: str | None = None,
        reasoning_mode: str = "off",
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self.writer_model = writer_model or model
        self.planner_model = planner_model or model
        # Vide = modèle du rôle planner (comportement historique de la relecture).
        self.proofreader_model = proofreader_model or self.planner_model
        self.fallback_model = fallback_model or model
        self.reasoning_mode = reasoning_mode or "off"

    def _extra_payload(self) -> dict:
        # Raisonnement activé par défaut sur deepseek-v4-flash : il consommait
        # ~99 % des tokens et tronquait les passes longues à la limite de
        # sortie. Le plafond reasoning.max_tokens est ignoré par ce modèle,
        # seule la désactivation est fiable. Réglable dans le CMS.
        if self.reasoning_mode == "off":
            return {"reasoning": {"enabled": False}}
        return {}

    def for_role(self, role: str) -> "OpenRouterLLMProvider":
        """Copie de ce provider pointant sur le modèle du rôle demandé
        ('writer' pour la rédaction, 'proofreader' pour la relecture,
        'planner' pour le reste). Retourne self quand le modèle du rôle est
        déjà le modèle courant."""
        if role == "writer":
            target = self.writer_model
        elif role == "proofreader":
            target = self.proofreader_model
        else:
            target = self.planner_model
        if not target or target == self.model:
            return self
        clone = copy.copy(self)
        clone.model = target
        clone.model_name = target
        clone.last_usage = None
        return clone
