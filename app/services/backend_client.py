"""
Async HTTP client for the Wasla Customer Portal API.

All methods return structured dicts:
- Success: {"status": "success", "data": <response JSON>}
- 204:     {"status": "success", "data": None}
- Error:   {"error": "<type>", "message": "<msg>"}
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("wasla.crm")

_client: httpx.AsyncClient | None = None


def _require_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("CRM client not initialized.")
    return _client


async def init_backend_client() -> None:
    global _client
    settings = get_settings()
    if not settings.crm_api_base_url:
        return
    if _client is not None:
        return
    _client = httpx.AsyncClient(
        base_url=settings.crm_api_base_url.rstrip("/"),
        timeout=settings.crm_api_timeout_seconds,
        headers={"Content-Type": "application/json"},
    )
    logger.info("CRM client connected to %s", settings.crm_api_base_url)


async def close_backend_client() -> None:
    global _client
    if _client is None:
        return
    await _client.aclose()
    _client = None


def is_configured() -> bool:
    return get_settings().crm_api_base_url != "" and _client is not None


def _auth_headers(bearer_token: str | None) -> dict[str, str]:
    if not bearer_token:
        return {}
    return {"Authorization": f"Bearer {bearer_token}"}


def _error_from_status(status_code: int, message: str | None = None) -> dict[str, str]:
    error_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "unprocessable",
        429: "rate_limited",
    }
    error = error_map.get(status_code, "service_error")
    return {"error": error, "message": message or "CRM API request failed."}


async def _request(
    method: str,
    path: str,
    *,
    bearer_token: str | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = _require_client()
    headers = _auth_headers(bearer_token)
    try:
        response = await client.request(method, path, params=params, json=json_body, headers=headers)
    except httpx.RequestError as exc:
        logger.exception("CRM request failed: %s", exc)
        return {"error": "service_error", "message": "CRM API is unavailable."}

    if 200 <= response.status_code < 300:
        if response.status_code == 204:
            return {"status": "success", "data": None}
        try:
            return {"status": "success", "data": response.json()}
        except ValueError:
            return {"status": "success", "data": {"raw": response.text}}

    try:
        err = response.json()
        message = err.get("message") or err.get("error") or response.text
    except ValueError:
        message = response.text
    return _error_from_status(response.status_code, message=message)


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def _clean_body(body: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in body.items() if v is not None}


# ── Auth ──────────────────────────────────────────────────────────

async def register(
    *, email: str, password: str, first_name: str, last_name: str, phone_number: str | None = None,
) -> dict[str, Any]:
    body = _clean_body({
        "email": email, "password": password,
        "firstName": first_name, "lastName": last_name, "phoneNumber": phone_number,
    })
    return await _request("POST", "/register", json_body=body)


async def login(*, email: str, password: str, remember_me: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {"email": email, "password": password}
    if remember_me:
        body["rememberMe"] = True
    return await _request("POST", "/login", json_body=body)


async def refresh_token(*, refresh_token_str: str) -> dict[str, Any]:
    return await _request("POST", "/refresh-token", json_body={"refreshToken": refresh_token_str})


async def logout(*, refresh_token_str: str) -> dict[str, Any]:
    return await _request("POST", "/logout", json_body={"refreshToken": refresh_token_str})


async def logout_all(bearer_token: str) -> dict[str, Any]:
    return await _request("POST", "/logout-all", bearer_token=bearer_token)


# ── Public: Companies ─────────────────────────────────────────────

async def list_companies(
    *, page_index: int | None = None, page_size: int | None = None,
    search: str | None = None, service_type: str | None = None, sort_by: str | None = None,
) -> dict[str, Any]:
    params = _clean_params({
        "pageIndex": page_index, "pageSize": page_size,
        "search": search, "serviceType": service_type, "sortBy": sort_by,
    })
    return await _request("GET", "/companies", params=params)


async def get_recommended_companies(
    *, page_index: int | None = None, page_size: int | None = None, service_type: str | None = None,
) -> dict[str, Any]:
    params = _clean_params({"pageIndex": page_index, "pageSize": page_size, "serviceType": service_type})
    return await _request("GET", "/recommended-companies", params=params)


async def get_trending_companies(
    *, page_index: int | None = None, page_size: int | None = None, service_type: str | None = None,
) -> dict[str, Any]:
    params = _clean_params({"pageIndex": page_index, "pageSize": page_size, "serviceType": service_type})
    return await _request("GET", "/trending-companies", params=params)


async def get_company_details(company_id: int) -> dict[str, Any]:
    return await _request("GET", f"/companies/{company_id}")


async def get_company_reviews(
    company_id: int, *, page_index: int | None = None, page_size: int | None = None, sort_by: str | None = None,
) -> dict[str, Any]:
    params = _clean_params({"pageIndex": page_index, "pageSize": page_size, "sortBy": sort_by})
    return await _request("GET", f"/companies/{company_id}/reviews", params=params)


# ── Reviews ───────────────────────────────────────────────────────

async def submit_review(
    bearer_token: str, company_id: int, *, rating: int, review_text: str | None = None,
) -> dict[str, Any]:
    body = _clean_body({"rating": rating, "reviewText": review_text})
    return await _request("POST", f"/companies/{company_id}/reviews", bearer_token=bearer_token, json_body=body)


async def update_review(
    bearer_token: str, company_id: int, *, rating: int, review_text: str | None = None,
) -> dict[str, Any]:
    body = _clean_body({"rating": rating, "reviewText": review_text})
    return await _request("PUT", f"/companies/{company_id}/reviews", bearer_token=bearer_token, json_body=body)


async def delete_review(bearer_token: str, company_id: int) -> dict[str, Any]:
    return await _request("DELETE", f"/companies/{company_id}/reviews", bearer_token=bearer_token)


async def get_my_reviews(
    bearer_token: str, *, page_index: int | None = None, page_size: int | None = None,
) -> dict[str, Any]:
    params = _clean_params({"pageIndex": page_index, "pageSize": page_size})
    return await _request("GET", "/my/reviews", bearer_token=bearer_token, params=params)


# ── Profiles ──────────────────────────────────────────────────────

async def get_customer_profile(bearer_token: str) -> dict[str, Any]:
    return await _request("GET", "/my/profile", bearer_token=bearer_token)


async def update_customer_profile(bearer_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await _request("PUT", "/my/profile", bearer_token=bearer_token, json_body=payload)


async def get_lead_profile(bearer_token: str) -> dict[str, Any]:
    return await _request("GET", "/my/lead-profile", bearer_token=bearer_token)


async def update_lead_profile(bearer_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await _request("PUT", "/my/lead-profile", bearer_token=bearer_token, json_body=payload)


async def get_digital_signature(bearer_token: str, *, password: str) -> dict[str, Any]:
    return await _request("POST", "/my/digital-signature", bearer_token=bearer_token, json_body={"password": password})


# ── Offers ────────────────────────────────────────────────────────

async def get_my_offers(
    bearer_token: str, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None,
) -> dict[str, Any]:
    params = _clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status})
    return await _request("GET", "/my/offers", bearer_token=bearer_token, params=params)


async def get_offer_details(bearer_token: str, offer_id: int) -> dict[str, Any]:
    return await _request("GET", f"/my/offers/{offer_id}", bearer_token=bearer_token)


async def accept_offer(
    bearer_token: str, offer_id: int, *, digital_signature: str, payment_method: int,
) -> dict[str, Any]:
    body = {"digitalSignature": digital_signature, "paymentMethod": payment_method}
    return await _request("POST", f"/my/offers/{offer_id}/accept", bearer_token=bearer_token, json_body=body)


async def reject_offer(bearer_token: str, offer_id: int, *, rejection_reason: str) -> dict[str, Any]:
    return await _request("POST", f"/my/offers/{offer_id}/reject", bearer_token=bearer_token, json_body={"rejectionReason": rejection_reason})


# ── Dashboard ─────────────────────────────────────────────────────

async def get_dashboard(bearer_token: str) -> dict[str, Any]:
    return await _request("GET", "/my/dashboard", bearer_token=bearer_token)


# ── Service Requests ──────────────────────────────────────────────

async def create_service_request(
    bearer_token: str, *,
    company_id: int, preferred_date: str | None = None,
    origin_address: str | None = None, destination_address: str | None = None, notes: str | None = None,
) -> dict[str, Any]:
    body = _clean_body({
        "companyId": company_id, "preferredDate": preferred_date,
        "originAddress": origin_address, "destinationAddress": destination_address, "notes": notes,
    })
    return await _request("POST", "/service-requests", bearer_token=bearer_token, json_body=body)


async def get_my_service_requests(
    bearer_token: str, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None,
) -> dict[str, Any]:
    params = _clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status})
    return await _request("GET", "/my/service-requests", bearer_token=bearer_token, params=params)


async def get_service_request_details(bearer_token: str, request_id: int) -> dict[str, Any]:
    return await _request("GET", f"/my/service-requests/{request_id}", bearer_token=bearer_token)
