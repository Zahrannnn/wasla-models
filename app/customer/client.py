"""Async HTTP client for the Wasla Customer Portal API."""

from __future__ import annotations

from typing import Any

from app.shared.http_client import BaseApiClient


class CustomerClient(BaseApiClient):
    """Customer Portal API client — extends BaseApiClient with domain methods."""

    # ── Auth ──────────────────────────────────────────────────────

    async def register(
        self, *, email: str, password: str, first_name: str, last_name: str,
        phone_number: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({
            "email": email, "password": password,
            "firstName": first_name, "lastName": last_name,
            "phoneNumber": phone_number,
        })
        return await self.request("POST", "/register", body=body)

    async def login(self, *, email: str, password: str, remember_me: bool = False) -> dict[str, Any]:
        body: dict[str, Any] = {"email": email, "password": password}
        if remember_me:
            body["rememberMe"] = True
        return await self.request("POST", "/login", body=body)

    async def refresh_token(self, *, refresh_token_str: str) -> dict[str, Any]:
        return await self.request("POST", "/refresh-token", body={"refreshToken": refresh_token_str})

    async def logout(self, *, refresh_token_str: str) -> dict[str, Any]:
        return await self.request("POST", "/logout", body={"refreshToken": refresh_token_str})

    async def logout_all(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("POST", "/logout-all", bearer=bearer_token)

    # ── Public: Companies ─────────────────────────────────────────

    async def list_companies(
        self, *, page_index: int | None = None, page_size: int | None = None,
        search: str | None = None, service_type: str | None = None, sort_by: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({
            "pageIndex": page_index, "pageSize": page_size,
            "search": search, "serviceType": service_type, "sortBy": sort_by,
        })
        return await self.request("GET", "/companies", params=params)

    async def get_recommended_companies(
        self, *, page_index: int | None = None, page_size: int | None = None,
        service_type: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "serviceType": service_type})
        return await self.request("GET", "/recommended-companies", params=params)

    async def get_trending_companies(
        self, *, page_index: int | None = None, page_size: int | None = None,
        service_type: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "serviceType": service_type})
        return await self.request("GET", "/trending-companies", params=params)

    async def get_company_details(self, company_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/companies/{company_id}")

    async def get_company_reviews(
        self, company_id: int, *, page_index: int | None = None,
        page_size: int | None = None, sort_by: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "sortBy": sort_by})
        return await self.request("GET", f"/companies/{company_id}/reviews", params=params)

    # ── Reviews ───────────────────────────────────────────────────

    async def submit_review(
        self, bearer_token: str, company_id: int, *, rating: int, review_text: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({"rating": rating, "reviewText": review_text})
        return await self.request("POST", f"/companies/{company_id}/reviews", bearer=bearer_token, body=body)

    async def update_review(
        self, bearer_token: str, company_id: int, *, rating: int, review_text: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({"rating": rating, "reviewText": review_text})
        return await self.request("PUT", f"/companies/{company_id}/reviews", bearer=bearer_token, body=body)

    async def delete_review(self, bearer_token: str, company_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/companies/{company_id}/reviews", bearer=bearer_token)

    async def get_my_reviews(
        self, bearer_token: str, *, page_index: int | None = None, page_size: int | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size})
        return await self.request("GET", "/my/reviews", bearer=bearer_token, params=params)

    # ── Profiles ──────────────────────────────────────────────────

    async def get_customer_profile(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("GET", "/my/profile", bearer=bearer_token)

    async def update_customer_profile(self, bearer_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PUT", "/my/profile", bearer=bearer_token, body=payload)

    async def get_lead_profile(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("GET", "/my/lead-profile", bearer=bearer_token)

    async def update_lead_profile(self, bearer_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PUT", "/my/lead-profile", bearer=bearer_token, body=payload)

    async def get_digital_signature(self, bearer_token: str, *, password: str) -> dict[str, Any]:
        return await self.request("POST", "/my/digital-signature", bearer=bearer_token, body={"password": password})

    # ── Offers ────────────────────────────────────────────────────

    async def get_my_offers(
        self, bearer_token: str, *, page_index: int | None = None,
        page_size: int | None = None, status: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status})
        return await self.request("GET", "/my/offers", bearer=bearer_token, params=params)

    async def get_offer_details(self, bearer_token: str, offer_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/my/offers/{offer_id}", bearer=bearer_token)

    async def accept_offer(
        self, bearer_token: str, offer_id: int, *, digital_signature: str, payment_method: int,
    ) -> dict[str, Any]:
        body = {"digitalSignature": digital_signature, "paymentMethod": payment_method}
        return await self.request("POST", f"/my/offers/{offer_id}/accept", bearer=bearer_token, body=body)

    async def reject_offer(self, bearer_token: str, offer_id: int, *, rejection_reason: str) -> dict[str, Any]:
        return await self.request("POST", f"/my/offers/{offer_id}/reject", bearer=bearer_token, body={"rejectionReason": rejection_reason})

    # ── Dashboard ─────────────────────────────────────────────────

    async def get_dashboard(self, bearer_token: str) -> dict[str, Any]:
        return await self.request("GET", "/my/dashboard", bearer=bearer_token)

    # ── Service Requests ──────────────────────────────────────────

    async def create_service_request(
        self, bearer_token: str, *,
        company_id: int, preferred_date: str | None = None,
        origin_address: str | None = None, destination_address: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        body = self.clean_body({
            "companyId": company_id, "preferredDate": preferred_date,
            "originAddress": origin_address, "destinationAddress": destination_address,
            "notes": notes,
        })
        return await self.request("POST", "/service-requests", bearer=bearer_token, body=body)

    async def get_my_service_requests(
        self, bearer_token: str, *, page_index: int | None = None,
        page_size: int | None = None, status: str | None = None,
    ) -> dict[str, Any]:
        params = self.clean_params({"pageIndex": page_index, "pageSize": page_size, "status": status})
        return await self.request("GET", "/my/service-requests", bearer=bearer_token, params=params)

    async def get_service_request_details(self, bearer_token: str, request_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/my/service-requests/{request_id}", bearer=bearer_token)
