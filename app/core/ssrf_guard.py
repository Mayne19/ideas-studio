"""Garde-fou anti-SSRF pour toute URL fournie par un utilisateur et utilisée
côté serveur pour une requête HTTP sortante (project.domain, webhooks...).

Résout le hostname en IP avant de vérifier — bloquer seulement les IP
littérales (comme le faisait app/routers/webhooks.py à l'origine) laisse
passer un hostname DNS qui résout vers une IP privée."""
import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal"}


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast


def assert_safe_external_url(url: str, *, require_https: bool = True) -> None:
    """Lève HTTPException(400) si l'URL ne doit pas être requêtée côté serveur."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="URL invalide")

    if require_https and parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="L'URL doit utiliser HTTPS")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Schéma d'URL non autorisé")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(status_code=400, detail="URL invalide : hôte manquant")
    if hostname in _BLOCKED_HOSTNAMES:
        raise HTTPException(status_code=400, detail="URL non autorisée")

    if _is_blocked_ip(hostname):
        raise HTTPException(status_code=400, detail="URL pointe vers une adresse réseau interne")

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Impossible de résoudre l'hôte")

    for family, _, _, _, sockaddr in resolved:
        ip_str = sockaddr[0]
        if _is_blocked_ip(ip_str):
            raise HTTPException(status_code=400, detail="URL pointe vers une adresse réseau interne")
