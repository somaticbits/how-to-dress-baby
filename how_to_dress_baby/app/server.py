"""Threaded LAN image server; weather fetching is independent of Kindle requests."""

import hashlib
import json
import logging
import os
import threading
from dataclasses import asdict, replace
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from app import __version__
from app.config import Config
from app.models import Room, Snapshot, Weather
from app.render import battery_notice, page_for, render
from app.rules import fresh, recommend
from app.weather import HAClient, demo_snapshot, timestamp, utc_now

LOG = logging.getLogger(__name__)


def encode(snapshot: Snapshot) -> bytes:
    return json.dumps(
        asdict(snapshot),
        default=lambda value: value.isoformat() if isinstance(value, datetime) else value,
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def decode(raw: bytes) -> Snapshot:
    value = json.loads(raw)
    value.setdefault("parents_bedroom", None)
    for name in ("weather", "living_room", "bedroom", "parents_bedroom"):
        if value[name] is not None:
            value[name]["observed_at"] = timestamp(value[name]["observed_at"])
    if value["weather"]:
        value["weather"]["forecast_conditions"] = tuple(value["weather"]["forecast_conditions"])
    return Snapshot(
        weather=Weather(**value["weather"]) if value["weather"] else None,
        living_room=Room(**value["living_room"]) if value["living_room"] else None,
        bedroom=Room(**value["bedroom"]) if value["bedroom"] else None,
        fetched_at=timestamp(value["fetched_at"]),
        demo=value["demo"],
        warnings=tuple(value["warnings"]),
        parents_bedroom=Room(**value["parents_bedroom"]) if value["parents_bedroom"] else None,
    )


def atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Display:
    def __init__(self, config: Config):
        self.config = config
        self.lock = threading.Lock()
        self.refresh_lock = threading.Lock()
        self.stop = threading.Event()
        self.client = HAClient(config)
        self.cache = Path(config.cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.snapshot = Snapshot(None, None, None, utc_now())
        self.error = False
        self._images: dict[str, tuple[bytes, bytes]] = {}
        cached = self.cache / "snapshot.json"
        if cached.exists() and not config.demo:
            try:
                previous = decode(cached.read_bytes())
                # Never promote sample weather into a live installation.
                if not previous.demo:
                    self.snapshot = replace(
                        previous, warnings=("Données en cache ; connexion en cours.",)
                    )
                    self.error = True
            except (ValueError, KeyError, TypeError, OSError):
                LOG.warning("Ignoring invalid weather cache")

    def refresh(self, now: datetime | None = None) -> None:
        now = now or utc_now()
        with self.refresh_lock:
            try:
                snapshot = demo_snapshot(now) if self.config.demo else self.client.fetch(now)
                atomic_write(self.cache / "snapshot.json", encode(snapshot))
                error = False
            except Exception as exc:
                # Never log an authenticated URL, request body, or bearer token.
                LOG.warning("Weather refresh failed (%s)", type(exc).__name__)
                with self.lock:
                    snapshot = replace(
                        self.snapshot,
                        warnings=("Connexion HA indisponible : dernières données en cache.",),
                    )
                error = True
            with self.lock:
                self.snapshot = snapshot
                self.error = error

    def image(
        self,
        now: datetime | None = None,
        page: str = "auto",
        battery_level: int | None = None,
        charging: bool | None = None,
    ) -> tuple[bytes, str]:
        now = now or utc_now()
        selected = page_for(self.config, now) if page == "auto" else page
        if selected not in {"day", "night"}:
            raise ValueError("page must be auto, day, or night")
        with self.lock:
            advice = recommend(self.snapshot, self.config, now)
            # Re-render on data/date changes and whenever freshness crosses its
            # limit, including during network failure. Not on every HTTP poll.
            key = (
                encode(self.snapshot)
                + json.dumps(
                    {
                        "date": now.astimezone(ZoneInfo(self.config.timezone)).date().isoformat(),
                        "page": selected,
                        "baby_name": self.config.baby_name,
                        "before_day_start": now.astimezone(ZoneInfo(self.config.timezone)).strftime(
                            "%H:%M"
                        )
                        < self.config.day_start,
                        "advice": asdict(advice),
                        "bedroom_fresh": bool(
                            self.snapshot.bedroom
                            and fresh(
                                self.snapshot.bedroom.observed_at, now, self.config.max_age_minutes
                            )
                        ),
                        "parents_bedroom_fresh": bool(
                            self.snapshot.parents_bedroom
                            and fresh(
                                self.snapshot.parents_bedroom.observed_at,
                                now,
                                self.config.max_age_minutes,
                            )
                        ),
                    },
                    sort_keys=True,
                ).encode()
            )
            cached = self._images.get(selected)
            if cached is None or cached[0] != key:
                content = render(self.snapshot, self.config, now, page=selected)
                atomic_write(self.cache / f"{selected}.png", content)
                self._images[selected] = (key, content)
            content = self._images[selected][1]
            content = battery_notice(content, battery_level, charging)
            etag = '"' + hashlib.sha256(content).hexdigest() + '"'
            return content, etag

    def status(self) -> dict:
        now = utc_now()
        with self.lock:
            weather = self.snapshot.weather
            usable = bool(weather and fresh(weather.observed_at, now, self.config.max_age_minutes))
            bedroom = self.snapshot.bedroom
            bedroom_usable = bool(
                bedroom and fresh(bedroom.observed_at, now, self.config.max_age_minutes)
            )
            selected = page_for(self.config, now)
            active_usable = bedroom_usable if selected == "night" else usable
            parents_usable = bool(
                self.snapshot.parents_bedroom
                and fresh(
                    self.snapshot.parents_bedroom.observed_at, now, self.config.max_age_minutes
                )
            )
            if selected == "night" and self.config.parents_bedroom_entity:
                active_usable = active_usable and parents_usable
            advice = recommend(self.snapshot, self.config, now)
            return {
                "version": __version__,
                "status": "demo"
                if self.config.demo
                else ("ok" if active_usable and not self.error else "degraded"),
                "demo": self.config.demo,
                "active_page": selected,
                "weather_fresh": usable,
                "bedroom_fresh": bedroom_usable,
                "parents_bedroom_fresh": parents_usable,
                "last_successful_fetch": self.snapshot.fetched_at.isoformat(),
                "warnings": self.snapshot.warnings,
                "decision": {
                    "basis": "air_temperature",
                    "air_temperature": weather.temperature if usable else None,
                    "apparent_temperature": weather.apparent_temperature if usable else None,
                    "band": advice.band,
                    "wear": advice.outdoor,
                    "bring": advice.bring,
                    "caution": advice.caution,
                },
            }

    def worker(self) -> None:
        while not self.stop.wait(self.config.refresh_seconds):
            self.refresh()


def handler_for(display: Display) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(15)

        def do_GET(self) -> None:
            self.respond(head=False)

        def do_HEAD(self) -> None:
            self.respond(head=True)

        def respond(self, head: bool) -> None:
            url = urlsplit(self.path)
            path = url.path
            if path in {"/", "/display.png", "/day.png", "/night.png"}:
                page = {"/day.png": "day", "/night.png": "night"}.get(path, "auto")
                query = parse_qs(url.query)
                raw_level = query.get("batteryLevel", [""])[0]
                battery_level = (
                    int(raw_level)
                    if raw_level.isascii()
                    and raw_level.isdigit()
                    and len(raw_level) <= 3
                    and 0 <= int(raw_level) <= 100
                    else None
                )
                raw_charging = query.get("isCharging", [""])[0].strip().lower()
                charging = {
                    "yes": True,
                    "true": True,
                    "1": True,
                    "no": False,
                    "false": False,
                    "0": False,
                }.get(raw_charging)
                content, etag = display.image(
                    page=page, battery_level=battery_level, charging=charging
                )
                if self.headers.get("If-None-Match") == etag:
                    self.send_response(304)
                    self.send_header("ETag", etag)
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "no-cache")
            elif path == "/health":
                status = display.status()
                content = json.dumps(status).encode()
                self.send_response(503 if status["status"] == "degraded" else 200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
            else:
                self.send_error(404)
                return
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if not head:
                self.wfile.write(content)

        def log_message(self, fmt: str, *args: object) -> None:
            # Request query strings may contain device telemetry; omit them.
            LOG.debug("HTTP request completed")

    return Handler


def serve(config: Config) -> None:
    display = Display(config)
    display.refresh()
    server = ThreadingHTTPServer(("0.0.0.0", config.port), handler_for(display))
    threading.Thread(target=display.worker, daemon=True).start()
    LOG.info("Display listening on port %s (%s)", config.port, "demo" if config.demo else "live")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        display.stop.set()
        server.server_close()
