from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.traffic import TrafficCollect
from app.services.tracking_service import collect_traffic_event

router = APIRouter(tags=["tracking"])

_TRAFFIC_JS = r"""(function () {
  'use strict';

  var script = document.currentScript;
  if (!script) {
    var scripts = document.getElementsByTagName('script');
    script = scripts[scripts.length - 1];
  }

  var projectId = script.getAttribute('data-project-id');
  var trackingKey = script.getAttribute('data-tracking-key');
  if (!projectId || !trackingKey) return;

  var baseUrl = script.src.replace(/\/traffic\.js(\?.*)?$/, '');
  var ua = (navigator && navigator.userAgent) ? navigator.userAgent : '';

  var payload = {
    project_id: projectId,
    tracking_key: trackingKey,
    url: window.location.href,
    path: window.location.pathname,
    referrer: document.referrer || null,
    user_agent: ua
  };

  var collectUrl = baseUrl + '/api/traffic/collect';

  try {
    if (window.fetch) {
      fetch(collectUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true
      }).catch(function () {});
    } else {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', collectUrl, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(payload));
    }
  } catch (e) {}
})();
"""


@router.get("/traffic.js")
def serve_traffic_js():
    return Response(content=_TRAFFIC_JS, media_type="application/javascript")


@router.post("/api/traffic/collect")
def collect(data: TrafficCollect, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else ""
    collect_traffic_event(db, data, client_ip)
    return {"ok": True}
