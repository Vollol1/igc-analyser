#!/usr/bin/env python3
"""Shared dhv-xc.de HTTP client used by list_flights.py and download_igc.py."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

import requests

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore


DEFAULT_BASE_URL = "https://www.dhv-xc.de"
LOGIN_PATH = "/login"
LOGIN_API_PATH = "/api/xc/login/login"
FLIGHTS_API_PATH = "/api/fli/flights"
IGC_DOWNLOAD_PATH_TEMPLATE = "/flight/{id}/igc"
CSRF_TOKEN_RE = re.compile(r"jc\.token\s*=\s*['\"]([^'\"]+)['\"]")
PAGE_SIZE = 50


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_dotenv_if_available() -> None:
    """Load .env file from the project root when python-dotenv is installed."""
    if load_dotenv is None:
        return
    dotenv_path = _project_root() / ".env"
    load_dotenv(dotenv_path, override=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_csrf_token(html: str) -> str:
    match = CSRF_TOKEN_RE.search(html)
    if not match:
        raise RuntimeError("Could not extract CSRF token (jc.token) from login page")
    return match.group(1)


def api_url(base_url: str, path: str, params: Optional[dict[str, Any]] = None) -> str:
    url = urljoin(base_url, path)
    if params:
        url += "?" + urlencode(params, doseq=True)
    return url


def api_headers(csrf_token: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "X-Csrf-Token": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
    }


def resolve_credentials(
    username: Optional[str], password: Optional[str]
) -> tuple[str, str]:
    """Resolve credentials from arguments or environment variables."""
    username = username or os.environ.get("DHV_XC_USERNAME")
    password = password or os.environ.get("DHV_XC_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "DHV-XC credentials are required. Provide them via .env "
            "(DHV_XC_USERNAME / DHV_XC_PASSWORD), environment variables, "
            "or --username / --password. Never commit credentials to Git."
        )
    return username, password



class DhvXcClient:
    """Authenticated session wrapper around dhv-xc.de's kers.app API."""

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "igc-extractor/1.0 (private automation; contact: user@example.com)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
        })
        self.csrf_token: Optional[str] = None

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
        allow_redirects: bool = True,
        headers: Optional[dict[str, str]] = None,
    ) -> requests.Response:
        url = api_url(self.base_url, path, params)
        request_headers: dict[str, str] = dict(headers) if headers else {}
        if self.csrf_token:
            request_headers.update(api_headers(self.csrf_token))
        if json_body is not None:
            request_headers["Content-Type"] = "application/json"

        resp = self.session.request(
            method,
            url,
            headers=request_headers,
            data=data,
            files=files,
            json=json_body,
            allow_redirects=allow_redirects,
            timeout=60,
        )
        resp.raise_for_status()
        return resp

    def login(self) -> dict[str, Any]:
        """Authenticate with dhv-xc.de and keep the session alive."""
        login_page = self._request("GET", LOGIN_PATH)
        self.csrf_token = parse_csrf_token(login_page.text)
        logging.info("Fetched login page and CSRF token")

        form_data = {
            "uid": self.username,
            "pwd": self.password,
            "stay": "1",
            "dhvfetch": "0",
        }
        resp = self._request("POST", LOGIN_API_PATH, data=form_data)

        try:
            payload = resp.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Login response was not JSON (status {resp.status_code}). "
                "The API endpoint or login flow may have changed."
            ) from exc

        if not payload.get("success"):
            meta = payload.get("meta", {})
            message = payload.get("message") or meta.get("message") or "Unknown login error"
            code = meta.get("code", 0)
            raise RuntimeError(f"Login failed (code {code}): {message}")

        meta = payload.get("meta", {})
        if "token" in meta:
            self.csrf_token = meta["token"]
            logging.info("CSRF token refreshed by login response")

        logging.info("Login reported success")
        return payload

    def get_flight_page(
        self,
        start: int = 0,
        limit: int = PAGE_SIZE,
    ) -> dict[str, Any]:
        """Fetch a page of own flights (including private ones)."""
        navpars = {
            "start": start,
            "limit": limit,
            "sort": "FlightDate",
            "dir": "desc",
        }
        params: dict[str, Any] = {
            "mine": "1",
            "incpriv": "1",
            "navpars": json.dumps(navpars, separators=(",", ":")),
        }

        resp = self._request("GET", FLIGHTS_API_PATH, params=params)
        try:
            return resp.json()
        except ValueError as exc:
            raise RuntimeError(
                "Flight list response was not JSON. The API may have changed."
            ) from exc

    def get_igc(self, flight_id: int) -> requests.Response:
        """Download the IGC file for a given flight using the authenticated session."""
        return self._request(
            "GET",
            IGC_DOWNLOAD_PATH_TEMPLATE.format(id=flight_id),
            headers={"Accept": "*/*"},
        )
