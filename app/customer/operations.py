"""Tool operations — Customer Portal API."""

from __future__ import annotations

from typing import Any

from app.shared.auth import require_bearer


# ── Auth ──────────────────────────────────────────────────────────

async def register_customer(ctx: dict, *, email: str, password: str, first_name: str, last_name: str, phone_number: str | None = None) -> dict:
    return await ctx["client"].register(email=email, password=password, first_name=first_name, last_name=last_name, phone_number=phone_number)


async def login_customer(ctx: dict, *, email: str, password: str, remember_me: bool = False) -> dict:
    return await ctx["client"].login(email=email, password=password, remember_me=remember_me)


async def refresh_token(ctx: dict, *, refresh_token: str) -> dict:
    return await ctx["client"].refresh_token(refresh_token_str=refresh_token)


async def logout(ctx: dict, *, refresh_token: str) -> dict:
    return await ctx["client"].logout(refresh_token_str=refresh_token)


async def logout_all(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].logout_all(t)


# ── Company Discovery ─────────────────────────────────────────────

async def list_companies(ctx: dict, *, page_index: int | None = None, page_size: int | None = None,
                         search: str | None = None, service_type: str | None = None, sort_by: str | None = None) -> dict:
    return await ctx["client"].list_companies(page_index=page_index, page_size=page_size, search=search, service_type=service_type, sort_by=sort_by)


async def get_recommended_companies(ctx: dict, *, service_type: str | None = None,
                                     page_index: int | None = None, page_size: int | None = None) -> dict:
    return await ctx["client"].get_recommended_companies(page_index=page_index, page_size=page_size, service_type=service_type)


async def get_trending_companies(ctx: dict, *, service_type: str | None = None,
                                  page_index: int | None = None, page_size: int | None = None) -> dict:
    return await ctx["client"].get_trending_companies(page_index=page_index, page_size=page_size, service_type=service_type)


async def get_company_details(ctx: dict, *, company_id: int) -> dict:
    return await ctx["client"].get_company_details(company_id)


async def get_company_reviews(ctx: dict, *, company_id: int, page_index: int | None = None,
                               page_size: int | None = None, sort_by: str | None = None) -> dict:
    return await ctx["client"].get_company_reviews(company_id, page_index=page_index, page_size=page_size, sort_by=sort_by)


# ── Reviews ───────────────────────────────────────────────────────

async def submit_review(ctx: dict, *, company_id: int, rating: int, review_text: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].submit_review(t, company_id, rating=rating, review_text=review_text)


async def update_review(ctx: dict, *, company_id: int, rating: int, review_text: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].update_review(t, company_id, rating=rating, review_text=review_text)


async def delete_review(ctx: dict, *, company_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].delete_review(t, company_id)


async def get_my_reviews(ctx: dict, *, page_index: int | None = None, page_size: int | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_reviews(t, page_index=page_index, page_size=page_size)


# ── Profiles ──────────────────────────────────────────────────────

async def get_customer_profile(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_customer_profile(t)


async def update_customer_profile(ctx: dict, *, first_name: str, last_name: str,
                                   phone_number: str | None = None, address: str | None = None,
                                   city: str | None = None, zip_code: str | None = None, country: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
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
    return await ctx["client"].update_customer_profile(t, payload)


async def get_lead_profile(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_lead_profile(t)


async def update_lead_profile(ctx: dict, *, first_name: str, last_name: str,
                               phone_number: str | None = None, address: str | None = None,
                               city: str | None = None, zip_code: str | None = None, country: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
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
    return await ctx["client"].update_lead_profile(t, payload)


async def get_digital_signature(ctx: dict, *, password: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_digital_signature(t, password=password)


# ── Offers ────────────────────────────────────────────────────────

async def get_my_offers(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_offers(t, page_index=page_index, page_size=page_size, status=status)


async def get_offer_details(ctx: dict, *, offer_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_offer_details(t, offer_id)


async def accept_offer(ctx: dict, *, offer_id: int, digital_signature: str, payment_method: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    pm_map = {"cod": 0, "online": 1}
    pm_int = pm_map.get(payment_method.lower())
    if pm_int is None:
        return {"error": "bad_request", "message": "Invalid payment method. Use 'COD' or 'Online'."}
    return await ctx["client"].accept_offer(t, offer_id, digital_signature=digital_signature, payment_method=pm_int)


async def reject_offer(ctx: dict, *, offer_id: int, rejection_reason: str) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].reject_offer(t, offer_id, rejection_reason=rejection_reason)


async def get_dashboard(ctx: dict) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_dashboard(t)


# ── Service Requests ──────────────────────────────────────────────

async def create_service_request(ctx: dict, *, company_id: int, service_type: str,
                                  from_street: str | None = None, from_city: str | None = None,
                                  from_zip_code: str | None = None, from_country: str | None = None,
                                  to_street: str | None = None, to_city: str | None = None,
                                  to_zip_code: str | None = None, to_country: str | None = None,
                                  preferred_date: str | None = None, preferred_time_slot: str | None = None,
                                  notes: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    origin_parts = [p for p in [from_street, from_city, from_zip_code, from_country] if p]
    dest_parts = [p for p in [to_street, to_city, to_zip_code, to_country] if p]
    origin_address = ", ".join(origin_parts) if origin_parts else None
    destination_address = ", ".join(dest_parts) if dest_parts else None
    full_notes_parts = []
    if preferred_time_slot:
        full_notes_parts.append(f"Preferred time: {preferred_time_slot}")
    if service_type:
        full_notes_parts.append(f"Service type: {service_type}")
    if notes:
        full_notes_parts.append(notes)
    full_notes = ". ".join(full_notes_parts) if full_notes_parts else None
    return await ctx["client"].create_service_request(
        t, company_id=company_id, preferred_date=preferred_date,
        origin_address=origin_address, destination_address=destination_address, notes=full_notes,
    )


async def get_my_service_requests(ctx: dict, *, page_index: int | None = None, page_size: int | None = None, status: str | None = None) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_my_service_requests(t, page_index=page_index, page_size=page_size, status=status)


async def get_service_request_details(ctx: dict, *, service_request_id: int) -> dict:
    t = require_bearer(ctx)
    if isinstance(t, dict):
        return t
    return await ctx["client"].get_service_request_details(t, service_request_id)
