"""
Tool operations — Customer Portal API.

Each function receives a context dict with optional bearer_token,
then delegates to the CRM client. Returns a dict for JSON serialization.
"""

from __future__ import annotations

from typing import Any

from app.services import backend_client as crm


# ── Auth ──────────────────────────────────────────────────────────

async def register_customer(ctx: dict, *, email: str, password: str, first_name: str, last_name: str, phone_number: str | None = None) -> dict:
    return await crm.register(email=email, password=password, first_name=first_name, last_name=last_name, phone_number=phone_number)


async def login_customer(ctx: dict, *, email: str, password: str, remember_me: bool = False) -> dict:
    return await crm.login(email=email, password=password, remember_me=remember_me)


async def refresh_token(ctx: dict, *, refresh_token: str) -> dict:
    return await crm.refresh_token(refresh_token_str=refresh_token)


async def logout(ctx: dict, *, refresh_token: str) -> dict:
    return await crm.logout(refresh_token_str=refresh_token)


async def logout_all(ctx: dict) -> dict:
    token = ctx.get("bearer_token")
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.logout_all(token)


# ── Company Discovery ─────────────────────────────────────────────

async def list_companies(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                         search: str | None = None, service_type: str | None = None, sort_by: str | None = None) -> dict:
    return await crm.list_companies(page_index=page_index, page_size=page_size, search=search, service_type=service_type, sort_by=sort_by)


async def get_recommended_companies(ctx: dict, *, service_type: str | None = None,
                                     page_index: int | None = None, page_size: int | None = None) -> dict:
    return await crm.get_recommended_companies(page_index=page_index, page_size=page_size, service_type=service_type)


async def get_trending_companies(ctx: dict, *, service_type: str | None = None,
                                  page_index: int | None = None, page_size: int | None = None) -> dict:
    return await crm.get_trending_companies(page_index=page_index, page_size=page_size, service_type=service_type)


async def get_company_details(ctx: dict, *, company_id: int) -> dict:
    return await crm.get_company_details(company_id)


async def get_company_reviews(ctx: dict, *, company_id: int, page_index: int | None = None,
                               page_size: int | None = None, sort_by: str | None = None) -> dict:
    return await crm.get_company_reviews(company_id, page_index=page_index, page_size=page_size, sort_by=sort_by)


# ── Reviews ───────────────────────────────────────────────────────

def _require_token(ctx: dict) -> str | None:
    token = ctx.get("bearer_token")
    return token


async def submit_review(ctx: dict, *, company_id: int, rating: int, review_text: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.submit_review(token, company_id, rating=rating, review_text=review_text)


async def update_review(ctx: dict, *, company_id: int, rating: int, review_text: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.update_review(token, company_id, rating=rating, review_text=review_text)


async def delete_review(ctx: dict, *, company_id: int) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.delete_review(token, company_id)


async def get_my_reviews(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_my_reviews(token, page_index=page_index, page_size=page_size)


# ── Profiles ──────────────────────────────────────────────────────

async def get_customer_profile(ctx: dict) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_customer_profile(token)


async def update_customer_profile(ctx: dict, *, first_name: str, last_name: str,
                                   phone_number: str | None = None, address: str | None = None,
                                   city: str | None = None, zip_code: str | None = None, country: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    payload: dict[str, Any] = {"firstName": first_name, "lastName": last_name}
    if phone_number is not None:
        payload["phoneNumber"] = phone_number
    if address is not None:
        payload["address"] = address
    if city is not None:
        payload["city"] = city
    if zip_code is not None:
        payload["zipCode"] = zip_code
    if country is not None:
        payload["country"] = country
    return await crm.update_customer_profile(token, payload)


async def get_lead_profile(ctx: dict) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_lead_profile(token)


async def update_lead_profile(ctx: dict, *, first_name: str, last_name: str,
                               phone_number: str | None = None, address: str | None = None,
                               city: str | None = None, zip_code: str | None = None, country: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    payload: dict[str, Any] = {"firstName": first_name, "lastName": last_name}
    if phone_number is not None:
        payload["phoneNumber"] = phone_number
    if address is not None:
        payload["address"] = address
    if city is not None:
        payload["city"] = city
    if zip_code is not None:
        payload["zipCode"] = zip_code
    if country is not None:
        payload["country"] = country
    return await crm.update_lead_profile(token, payload)


async def get_digital_signature(ctx: dict, *, password: str) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_digital_signature(token, password=password)


# ── Offers ────────────────────────────────────────────────────────

async def get_my_offers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_my_offers(token, page_index=page_index, page_size=page_size, status=status)


async def get_offer_details(ctx: dict, *, offer_id: int) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_offer_details(token, offer_id)


async def accept_offer(ctx: dict, *, offer_id: int, digital_signature: str, payment_method: str) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    # Map string payment_method to API int: COD=0, Online=1
    pm_map = {"cod": 0, "online": 1}
    pm_int = pm_map.get(payment_method.lower())
    if pm_int is None:
        return {"error": "bad_request", "message": "Invalid payment method. Use 'COD' or 'Online'."}
    return await crm.accept_offer(token, offer_id, digital_signature=digital_signature, payment_method=pm_int)


async def reject_offer(ctx: dict, *, offer_id: int, rejection_reason: str) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.reject_offer(token, offer_id, rejection_reason=rejection_reason)


async def get_dashboard(ctx: dict) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_dashboard(token)


# ── Service Requests ──────────────────────────────────────────────

async def create_service_request(ctx: dict, *, company_id: int, service_type: str,
                                  from_street: str | None = None, from_city: str | None = None,
                                  from_zip_code: str | None = None, from_country: str | None = None,
                                  to_street: str | None = None, to_city: str | None = None,
                                  to_zip_code: str | None = None, to_country: str | None = None,
                                  preferred_date: str | None = None, preferred_time_slot: str | None = None,
                                  notes: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    # Combine address parts into single strings for the CRM API
    origin_parts = [p for p in [from_street, from_city, from_zip_code, from_country] if p]
    dest_parts = [p for p in [to_street, to_city, to_zip_code, to_country] if p]
    origin_address = ", ".join(origin_parts) if origin_parts else None
    destination_address = ", ".join(dest_parts) if dest_parts else None
    # Combine date + time slot into notes if both present
    full_notes_parts = []
    if preferred_time_slot:
        full_notes_parts.append(f"Preferred time: {preferred_time_slot}")
    if service_type:
        full_notes_parts.append(f"Service type: {service_type}")
    if notes:
        full_notes_parts.append(notes)
    full_notes = ". ".join(full_notes_parts) if full_notes_parts else None
    return await crm.create_service_request(
        token, company_id=company_id, preferred_date=preferred_date,
        origin_address=origin_address, destination_address=destination_address, notes=full_notes,
    )


async def get_my_service_requests(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_my_service_requests(token, page_index=page_index, page_size=page_size, status=status)


async def get_service_request_details(ctx: dict, *, service_request_id: int) -> dict:
    token = _require_token(ctx)
    if not token:
        return {"error": "unauthorized", "message": "Authentication required. Please log in first."}
    return await crm.get_service_request_details(token, service_request_id)
