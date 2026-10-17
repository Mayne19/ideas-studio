"""Client HTTP du rédacteur local vers le CMS (bibliothèque standard seulement).

Authentification : jeton IDEAS_STUDIO_TOKEN, ou identifiants IDEAS_STUDIO_EMAIL
et IDEAS_STUDIO_PASSWORD (nouvelle connexion automatique si le jeton expire).
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_API = "https://ideas-studio-production.up.railway.app"


class CmsError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"CMS {status} : {detail}")
        self.status = status


class CmsClient:
    def __init__(self, project_id: str, *, api: str | None = None, token: str | None = None,
                 email: str | None = None, password: str | None = None, timeout: float = 60.0, opener=urlopen):
        self.api = (api or os.getenv("IDEAS_STUDIO_API") or DEFAULT_API).rstrip("/")
        self.project_id = project_id
        self.token = token or os.getenv("IDEAS_STUDIO_TOKEN")
        self.email = email or os.getenv("IDEAS_STUDIO_EMAIL")
        self.password = password or os.getenv("IDEAS_STUDIO_PASSWORD")
        self.timeout = timeout
        self._open = opener

    def _raw(self, method: str, path: str, body: dict | None = None, *, auth: bool = True):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(self.api + path, data=data, headers=headers, method=method)
        try:
            with self._open(request, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as exc:
            raise CmsError(exc.code, exc.read().decode("utf-8", errors="replace")[:300]) from exc
        return json.loads(raw) if raw else None

    def login(self) -> None:
        if not (self.email and self.password):
            raise CmsError(401, "jeton absent ou expiré et identifiants IDEAS_STUDIO_EMAIL / PASSWORD non fournis")
        self.token = self._raw("POST", "/auth/login", {"email": self.email, "password": self.password}, auth=False)["access_token"]

    def request(self, method: str, path: str, body: dict | None = None):
        if not self.token:
            self.login()
        try:
            return self._raw(method, path, body)
        except CmsError as exc:
            if exc.status != 401 or not (self.email and self.password):
                raise
            self.login()
            return self._raw(method, path, body)

    def _project(self, path: str) -> str:
        return f"/projects/{self.project_id}{path}"

    def jobs(self) -> list[dict]:
        return self.request("GET", self._project("/local-writer/jobs")) or []

    def site_articles(self) -> list[dict]:
        return self.request("GET", self._project("/local-writer/site-articles")) or []

    def deposit(self, article_id: str, markdown: str, fiche: dict | None, fiche_error: str = "") -> dict:
        return self.request("POST", self._project(f"/editorial-workflow/articles/{article_id}/deposit"),
                            {"markdown": markdown, "fiche": fiche, "fiche_error": fiche_error})

    def report(self, article_id: str, report: dict) -> dict:
        return self.request("POST", self._project(f"/local-writer/articles/{article_id}/report"), report)
