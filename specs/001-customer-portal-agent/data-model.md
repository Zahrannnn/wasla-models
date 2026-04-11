# Data Model: Customer Portal Agent

**Branch**: `001-customer-portal-agent` | **Date**: 2026-03-14

This document describes the data entities that the customer portal agent interacts with. These are **not** database models — they are the shapes of data returned by and sent to the Wasla CRM API. The agent layer deals only with these API-level representations.

---

## Entities

### Company

A registered service provider visible to customers.

| Field | Type | Description |
|-------|------|-------------|
| `companyId` | int | Unique identifier |
| `companyName` | string | Display name |
| `serviceTypes` | string[] | Services offered (Moving, Cleaning, Disposal, etc.) |
| `rating` | float | Aggregate customer rating |
| `logoUrl` | string | Company logo URL |
| `description` | string | Company description |
| `serviceCatalog` | ServiceItem[] | Available services with details |

**Source endpoints**: GET /companies, GET /recommended-companies, GET /trending-companies, GET /companies/{companyId}

---

### Review

A customer's rating and feedback for a company.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `reviewId` | int | | Unique identifier |
| `companyId` | int | | Target company |
| `customerId` | int | | Author |
| `rating` | int | 1–5 | Star rating |
| `reviewText` | string | Optional; moderated | Textual feedback |
| `createdAt` | datetime | | Submission timestamp |
| `updatedAt` | datetime | | Last edit timestamp |

**Validation rules**:
- One review per customer per company (409 Conflict on duplicate)
- Review text must pass server-side content moderation (400 on rejection)

**Source endpoints**: GET /companies/{companyId}/reviews, GET /my/reviews, POST/PUT/DELETE /companies/{companyId}/reviews

---

### Service Request

A customer's inquiry submitted to a specific company.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | int | | Unique identifier |
| `companyId` | int | Yes | Target company |
| `customerId` | int | | Requesting customer |
| `preferredDate` | datetime | No | Preferred service date |
| `originAddress` | string | No | Pick-up location |
| `destinationAddress` | string | No | Delivery location |
| `notes` | string | No | Additional instructions |
| `status` | string | | Current status |
| `createdAt` | datetime | | Submission timestamp |

**State transitions**:

```
Pending → Declined     (company rejects)
Pending → OfferSent    (company sends offer)
OfferSent → Closed     (offer accepted or request completed)
```

**Source endpoints**: POST /service-requests, GET /my/service-requests, GET /my/service-requests/{id}

---

### Offer

A company's proposal in response to a service request.

| Field | Type | Description |
|-------|------|-------------|
| `offerId` | int | Unique identifier |
| `companyId` | int | Originating company |
| `companyName` | string | Company display name |
| `customerId` | int | Target customer |
| `serviceLineItems` | LineItem[] | Itemized services and pricing |
| `totalAmount` | decimal | Total price |
| `status` | string | Current status |
| `createdAt` | datetime | When offer was created |

**State transitions**:

```
Pending → Sent        (company sends to customer)
Sent → Accepted       (customer accepts with signature + payment)
Sent → Rejected       (customer rejects with reason)
Sent → Canceled       (company or system cancels)
Accepted/Rejected/Canceled → (terminal — no further transitions)
```

**Acceptance requires**:
- `digitalSignature`: string, format `SIG-XXXXX-XXXXX`
- `paymentMethod`: int, `0` (COD) or `1` (Online/Stripe)

**Source endpoints**: GET /my/offers, GET /my/offers/{offerId}, POST /my/offers/{offerId}/accept, POST /my/offers/{offerId}/reject

---

### LineItem (nested in Offer)

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Service description |
| `quantity` | int | Number of units |
| `unitPrice` | decimal | Price per unit |
| `total` | decimal | Line total |

---

### Customer Profile

| Field | Type | Description |
|-------|------|-------------|
| `customerId` | int | Unique identifier |
| `companyId` | int | Company scope |
| `firstName` | string | |
| `lastName` | string | |
| `email` | string | |
| `phoneNumber` | string | |
| `address` | string | |
| `city` | string | |
| `zipCode` | string | |
| `country` | string | |

**Source endpoints**: GET /my/profile, PUT /my/profile

---

### Lead Profile

A lead's personal profile with multi-company connection history.

| Field | Type | Description |
|-------|------|-------------|
| `userId` | int | Auth user ID |
| `leadId` | int | Lead identifier |
| `firstName` | string | |
| `lastName` | string | |
| `email` | string | |
| `phoneNumber` | string | |
| `address` | string | |
| `city` | string | |
| `zipCode` | string | |
| `country` | string | |
| `createdAt` | datetime | Registration date |
| `companies` | LeadCompanyConnection[] | All company connections |

**Source endpoints**: GET /my/lead-profile, PUT /my/lead-profile

---

### LeadCompanyConnection (nested in Lead Profile)

| Field | Type | Description |
|-------|------|-------------|
| `leadCompanyId` | int | Connection ID |
| `companyId` | int | Connected company |
| `companyName` | string | Company display name |
| `companyLogoUrl` | string | Company logo |
| `status` | string | Pending, Accepted, or Rejected |
| `customerId` | int | Associated customer record (if accepted) |
| `requestedAt` | datetime | When connection was requested |
| `respondedAt` | datetime | When company responded |

---

### Dashboard

Summary metrics for the customer portal.

| Field | Type | Description |
|-------|------|-------------|
| `openRequests` | int | Count of pending service requests |
| `activeOffers` | int | Count of non-terminal offers |
| `recentActivity` | ActivityItem[] | Recent actions/events |

**Source endpoints**: GET /my/dashboard

---

## Entity Relationships

```
Lead ──< LeadCompanyConnection >── Company
                |
                v
            Customer ──< ServiceRequest >── Company
                |              |
                |              v
                |           Offer ──< LineItem
                |
                └──< Review >── Company
```

- A Lead can be connected to multiple Companies (via LeadCompanyConnection)
- Each accepted connection creates a Customer record for that Lead+Company pair
- A Customer submits ServiceRequests to a Company
- A Company responds to ServiceRequests with Offers
- A Customer writes Reviews for Companies (one per company)
