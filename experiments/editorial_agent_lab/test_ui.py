"""Interface locale minimaliste pour lancer un essai du laboratoire."""

from __future__ import annotations

import argparse
import json
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .editorial_agent.live_runner import LiveRunConfig, LiveRunError, run_live


ROOT = Path(__file__).resolve().parent
RUN_ROOT = ROOT / "run" / "ui"
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


PAGE = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Editorial Agent Lab</title>
  <style>
    :root { color-scheme: light; font-family: Inter, system-ui, sans-serif; }
    body { margin: 0; background: #f4f1eb; color: #202124; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px 70px; }
    h1 { margin: 0 0 8px; font: 700 31px/1.1 Georgia, serif; }
    .lead { color: #68635c; margin: 0 0 24px; }
    .panel { background: #fffdf9; border: 1px solid #ddd5c9; border-radius: 14px;
      box-shadow: 0 8px 24px #4b3f2a12; padding: 20px; }
    form { display: grid; gap: 14px; }
    label { display: grid; gap: 6px; font-size: 13px; font-weight: 650; color: #514b43; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #cfc5b8;
      border-radius: 8px; background: #fff; padding: 11px 12px; font: inherit; }
    textarea { min-height: 86px; resize: vertical; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    button { width: fit-content; border: 0; border-radius: 8px; padding: 11px 18px;
      background: #394f61; color: #fff; font-weight: 700; cursor: pointer; }
    button:disabled { opacity: .55; cursor: wait; }
    .chat { display: grid; gap: 12px; margin-top: 22px; }
    .bubble { border-radius: 13px; padding: 14px 16px; white-space: pre-wrap; }
    .user { background: #e6ddd0; margin-left: 12%; }
    .agent { background: #fff; border: 1px solid #ddd5c9; margin-right: 12%; }
    .hidden { display: none; }
    iframe { width: 100%; height: 760px; border: 1px solid #ddd5c9; border-radius: 10px; background: #fff; }
    a { color: #315d78; }
    .small { color: #716b62; font-size: 13px; }
    @media (max-width: 680px) { .grid { grid-template-columns: 1fr; } .user, .agent { margin: 0; } }
  </style>
</head>
<body>
<main>
  <h1>Editorial Agent Lab</h1>
  <p class="lead">Un essai isolé : un mot-clé, une exécution complète, un article et son rapport.</p>
  <section class="panel">
    <form id="run-form">
      <label>Sujet ou mot-clé
        <input id="keyword" required autofocus placeholder="Ex. comment choisir un casque audio">
      </label>
      <button id="submit" type="submit">Lancer l’essai</button>
    </form>
  </section>
  <section id="chat" class="chat"></section>
  <section id="result" class="panel hidden">
    <h2>Article généré</h2>
    <p id="links" class="small"></p>
    <iframe id="article" title="Article généré"></iframe>
  </section>
</main>
<script>
const form = document.getElementById('run-form');
const submit = document.getElementById('submit');
const chat = document.getElementById('chat');
const result = document.getElementById('result');
const links = document.getElementById('links');
const article = document.getElementById('article');
function bubble(kind, text) {
  const node = document.createElement('div');
  node.className = 'bubble ' + kind;
  node.textContent = text;
  chat.appendChild(node);
  node.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  return node;
}
function value(id) { return document.getElementById(id).value.trim(); }
async function poll(id, node) {
  const response = await fetch('/api/runs/' + id);
  const job = await response.json();
  if (job.status === 'running') {
    node.textContent = 'L’algorithme travaille : recherche, lecture, analyse, rédaction et contrôles…';
    setTimeout(() => poll(id, node), 2000);
    return;
  }
  submit.disabled = false;
  if (job.status === 'succeeded') {
    node.textContent = 'Article terminé. Le rapport et le rendu sont disponibles ci-dessous.';
    result.classList.remove('hidden');
    article.src = job.article_url;
    links.innerHTML = '<a target="_blank" href="' + job.article_url + '">Ouvrir l’article</a> · '
      + '<a target="_blank" href="' + job.report_url + '">Ouvrir le rapport JSON</a>';
  } else {
    node.textContent = job.status === 'blocked' ? 'Essai bloqué : ' + job.error : 'Échec : ' + job.error;
  }
}
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submit.disabled = true;
  bubble('user', value('keyword'));
  const status = bubble('agent', 'Préparation de l’essai…');
  const response = await fetch('/api/runs', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({keyword: value('keyword')})});
  const job = await response.json();
  if (!response.ok) { submit.disabled = false; status.textContent = job.error; return; }
  poll(job.id, status);
});
</script>
</body>
</html>"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_run_id(value: str) -> bool:
    return len(value) == 32 and all(char in "0123456789abcdef" for char in value)


def _start_job(payload: dict) -> dict:
    keyword = str(payload.get("keyword") or "").strip()
    if not keyword:
        raise ValueError("Le mot-clé est obligatoire.")
    run_id = uuid.uuid4().hex
    output_dir = RUN_ROOT / run_id
    config = LiveRunConfig(
        keyword=keyword,
        site_name=str(payload.get("site_name") or "Ideas Studio").strip(),
        domain=str(payload.get("domain") or "example.com").strip(),
        category=str(payload.get("category") or "").strip(),
        project_id=str(payload.get("project_id") or "").strip() or None,
        editor_notes=str(payload.get("editor_notes") or "").strip(),
        output_dir=output_dir,
    )
    job = {"id": run_id, "status": "running", "keyword": keyword, "created_at": _now(), "error": ""}
    with JOBS_LOCK:
        JOBS[run_id] = job

    def worker() -> None:
        try:
            report = run_live(config)
            with JOBS_LOCK:
                job.update({"status": "succeeded", "finished_at": _now(), "report": report})
        except LiveRunError as exc:
            with JOBS_LOCK:
                job.update({"status": "blocked", "finished_at": _now(), "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - l'interface doit exposer l'échec du run
            with JOBS_LOCK:
                job.update({"status": "failed", "finished_at": _now(), "error": str(exc)})

    threading.Thread(target=worker, name=f"editorial-lab-{run_id[:8]}", daemon=True).start()
    return {"id": run_id, "status": "running"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[editorial-lab] {format % args}")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file() or RUN_ROOT not in path.parents:
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/" or path == "/index.html":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] == "runs" and _safe_run_id(parts[2]):
            with JOBS_LOCK:
                job = dict(JOBS.get(parts[2]) or {})
            if not job:
                self._json({"error": "Essai introuvable."}, 404)
                return
            report = job.get("report") or {}
            output = report.get("output") or {}
            self._json({
                "id": job["id"], "status": job["status"], "keyword": job["keyword"],
                "error": job.get("error", ""),
                "article_url": f"/runs/{parts[2]}/article.html" if output else "",
                "report_url": f"/runs/{parts[2]}/report.json" if output else "",
            })
            return
        if len(parts) == 3 and parts[0] == "runs" and _safe_run_id(parts[1]) and parts[2] in {"article.html", "report.json"}:
            content_type = "text/html; charset=utf-8" if parts[2].endswith(".html") else "application/json; charset=utf-8"
            self._file(RUN_ROOT / parts[1] / parts[2], content_type)
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/runs":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._json(_start_job(payload), 202)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Editorial Agent Lab : http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
