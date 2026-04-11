# Feature Specification: Customer Portal Agent Prompt

**Feature Branch**: `001-customer-portal-agent`  
**Created**: 2026-03-14  
**Status**: Draft  
**Input**: User description: "Build an AI agent prompt and complete API endpoint integration for the Wasla CRM Customer Portal. The agent acts on behalf of customers to discover service companies, manage service requests, handle offers, manage profiles, write reviews, and track service history."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover and Compare Service Companies (Priority: P1)

A customer asks the AI agent to help them find service companies for a specific need (e.g., moving from Zurich to Geneva). The agent searches available companies, presents results with ratings and service types, and allows the customer to drill into company profiles and reviews before making a decision.

**Why this priority**: Company discovery is the entry point of the entire customer journey. Without the ability to find and evaluate companies, no downstream actions (requests, offers, reviews) are possible. This is also the only flow that works without authentication, making it the lowest-friction starting point.

**Independent Test**: Can be fully tested by asking the agent to search for moving companies, viewing a company profile, and reading reviews — all using public endpoints with no authentication required.

**Acceptance Scenarios**:

1. **Given** a customer asks for moving services, **When** the agent searches companies filtered by service type, **Then** the agent presents a paginated list of companies with name, rating, and service type.
2. **Given** a customer wants to compare companies, **When** the agent retrieves recommended or trending companies, **Then** the results are ranked by composite score or improvement delta respectively.
3. **Given** a customer selects a company, **When** the agent fetches the company profile, **Then** the full profile including service catalog is displayed.
4. **Given** a customer wants to see feedback, **When** the agent fetches company reviews, **Then** reviews are displayed with rating, text, and sort options (newest or highest-rated).
5. **Given** a customer asks for a company that does not exist, **When** the agent fetches the profile, **Then** the agent gracefully explains the company was not found.

---

### User Story 2 - Submit a Service Request (Priority: P2)

After discovering a company, the customer tells the agent they want to request service. The agent gathers required details (preferred date, pickup/delivery addresses, notes) and submits the service request on the customer's behalf.

**Why this priority**: Service request submission is the primary conversion action — it turns a browsing customer into an engaged lead. This is the core value proposition of the portal.

**Independent Test**: Can be tested by authenticating, selecting a known company, providing service details, and confirming the request was submitted successfully.

**Acceptance Scenarios**:

1. **Given** an authenticated customer has selected a company, **When** they provide service details (date, addresses, notes), **Then** the agent submits the request and confirms success.
2. **Given** a customer provides incomplete details, **When** the agent prepares the request, **Then** the agent prompts for missing information before submitting.
3. **Given** the target company is not found or inactive, **When** the agent submits the request, **Then** the agent explains the company is unavailable and suggests alternatives.
4. **Given** the customer is not authenticated, **When** they attempt to submit a request, **Then** the agent prompts for authentication first.
5. **Given** a customer wants to track submitted requests, **When** the agent retrieves the request list, **Then** requests are shown with status, dates, and company names.

---

### User Story 3 - Manage Offers (Priority: P2)

A customer receives offers from companies in response to their service requests. They ask the agent to show pending offers, review offer details (including line items and pricing), and then accept or reject offers. For acceptance, the agent collects the digital signature and payment method choice.

**Why this priority**: Offer management is the revenue-generating step. Accepting offers completes the service transaction. This has equal weight with service requests as both are required for the end-to-end flow.

**Independent Test**: Can be tested by listing pending offers, viewing details of a specific offer, accepting one offer (with COD or Online payment), and rejecting another with a reason.

**Acceptance Scenarios**:

1. **Given** an authenticated customer, **When** they ask to see pending offers, **Then** the agent displays a filtered list of offers with status, amounts, and company names.
2. **Given** a customer selects an offer, **When** the agent retrieves details, **Then** the full offer is shown including service line items and total amount.
3. **Given** a customer wants to accept an offer with COD, **When** they provide their digital signature and select COD, **Then** the offer is accepted immediately and confirmation is shown.
4. **Given** a customer wants to accept an offer with online payment, **When** they provide their digital signature and select Online, **Then** the agent returns a Stripe checkout URL and explains that acceptance completes after payment.
5. **Given** a customer provides an invalid digital signature, **When** the agent submits acceptance, **Then** the agent explains the signature is invalid and asks for correction.
6. **Given** the offer is already in a terminal state (accepted/rejected/cancelled), **When** the agent attempts to accept or reject it, **Then** the agent explains the offer can no longer be modified.
7. **Given** a customer wants to reject an offer, **When** they provide a rejection reason, **Then** the offer is transitioned to Rejected and the customer receives confirmation.
8. **Given** online payment is selected but the company lacks payment configuration, **When** the agent submits acceptance, **Then** the agent explains the issue and suggests COD as an alternative.

---

### User Story 4 - Write and Manage Reviews (Priority: P3)

After receiving service, a customer wants to leave a review for a company. The agent helps them submit, update, or delete reviews. The agent also allows viewing all reviews the customer has written.

**Why this priority**: Reviews are important for community trust but are not on the critical path of service delivery. They enhance the ecosystem but are not required for the core transaction flow.

**Independent Test**: Can be tested by submitting a review for a company, viewing it in "my reviews," updating the rating, and then deleting it.

**Acceptance Scenarios**:

1. **Given** an authenticated customer wants to review a company, **When** they provide a rating (1-5) and optional text, **Then** the agent submits the review after content moderation passes.
2. **Given** the review text contains hateful or abusive content, **When** the agent submits the review, **Then** the agent explains the review was rejected by moderation and asks for revision.
3. **Given** a customer has already reviewed a company, **When** they try to submit a new review, **Then** the agent explains they already have a review and offers to update it instead.
4. **Given** a customer wants to edit their existing review, **When** they provide updated rating/text, **Then** the agent updates the review (subject to moderation).
5. **Given** a customer wants to delete their review, **When** they confirm the action, **Then** the review is removed.
6. **Given** a customer wants to see all their reviews, **When** the agent retrieves "my reviews," **Then** reviews across all companies are displayed with pagination.

---

### User Story 5 - Manage Profile and Lead Information (Priority: P3)

A customer wants to view or update their personal profile or lead profile. The agent retrieves the current profile, allows edits, and shows connection history with companies.

**Why this priority**: Profile management is a supporting capability. Customers need it occasionally, but it does not drive core value. Lead profile viewing is useful for understanding multi-company connection status.

**Independent Test**: Can be tested by viewing the customer profile, updating a field, viewing the lead profile with company connections, and updating lead details.

**Acceptance Scenarios**:

1. **Given** an authenticated customer, **When** they ask to see their profile, **Then** the agent displays customer profile details.
2. **Given** a customer wants to update profile information, **When** they provide new values, **Then** the agent updates the profile and confirms changes.
3. **Given** a customer asks about their company connections, **When** the agent fetches the lead profile, **Then** all company connections are shown with status (Pending, Accepted, Rejected) and timestamps.
4. **Given** a customer updates their lead profile, **When** the changes are saved, **Then** the agent confirms that future customer records will be pre-filled with the updated information.

---

### User Story 6 - View Dashboard Summary (Priority: P3)

A customer wants a quick overview of their activity. The agent retrieves dashboard metrics including open requests, active offers, and recent activity.

**Why this priority**: The dashboard provides convenience and situational awareness but is a read-only summary. It enhances the experience but is not essential for any transactional flow.

**Independent Test**: Can be tested by asking the agent for a summary and verifying the dashboard metrics are returned and presented clearly.

**Acceptance Scenarios**:

1. **Given** an authenticated customer, **When** they ask for an overview or dashboard, **Then** the agent presents summary metrics: open requests count, active offers count, and recent activity.
2. **Given** a customer has no activity, **When** the dashboard is retrieved, **Then** the agent presents zero counts and suggests discovering companies or submitting a service request.

---

### Edge Cases

- What happens when the customer's authentication token expires mid-conversation? The agent should detect the 401 response and prompt the customer to re-authenticate.
- How does the system handle network timeouts or API unavailability? The agent should explain the temporary issue and suggest retrying.
- What happens when a customer tries to accept an offer using online payment but their session expires before completing the Stripe checkout? The offer remains in its pre-acceptance state; the agent should explain that the offer was not accepted and can be retried.
- What happens when the agent encounters an unexpected error code not documented in the API? The agent should present a generic error message and recommend contacting support.
- How does the agent handle concurrent actions (e.g., two offers being accepted simultaneously)? Each action is processed independently; terminal-state validation on the server prevents double-acceptance.
- What happens when content moderation service is unavailable during review submission? The review is rejected with a 400 error; the agent should explain the temporary issue and suggest retrying later.
- What happens when a customer asks the agent to perform an action for another customer? The agent should refuse and explain it can only act on behalf of the authenticated customer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST be able to search and list companies using public endpoints without requiring authentication, supporting filters for service type, search term, and sort order.
- **FR-002**: The agent MUST be able to retrieve recommended companies ranked by Bayesian composite score and trending companies based on recent review improvement.
- **FR-003**: The agent MUST be able to retrieve a company's full public profile including service catalog.
- **FR-004**: The agent MUST be able to retrieve paginated reviews for any company, with sort options (newest, highest-rated).
- **FR-005**: The agent MUST require authentication before executing any action on authenticated endpoints (service requests, offers, reviews, profiles, dashboard).
- **FR-006**: The agent MUST be able to submit a service request to a company on behalf of the customer, collecting required details (company ID, preferred date, addresses, notes) before submission.
- **FR-007**: The agent MUST be able to list and display the customer's offers, filtered by status, with full detail retrieval including service line items.
- **FR-008**: The agent MUST support accepting an offer by collecting the customer's digital signature (SIG-XXXXX-XXXXX format) and payment method choice (COD or Online).
- **FR-009**: For online payment acceptance, the agent MUST present the Stripe checkout URL and explain that the offer is only confirmed after payment completion.
- **FR-010**: The agent MUST support rejecting an offer with a mandatory rejection reason.
- **FR-011**: The agent MUST be able to submit, update, and delete reviews on behalf of the customer, with ratings from 1 to 5 and optional review text.
- **FR-012**: The agent MUST handle content moderation rejection for reviews and explain the reason to the customer.
- **FR-013**: The agent MUST enforce the one-review-per-customer-per-company constraint by detecting 409 Conflict responses and offering to update the existing review instead.
- **FR-014**: The agent MUST be able to retrieve and update the customer profile and lead profile, including viewing all company connection history.
- **FR-015**: The agent MUST be able to retrieve customer dashboard summary metrics.
- **FR-016**: The agent MUST confirm with the customer before executing any state-changing action (accepting/rejecting offers, submitting reviews, submitting service requests).
- **FR-017**: The agent MUST handle all documented error codes (400, 401, 404, 409, 422) with user-friendly explanations and appropriate recovery suggestions.
- **FR-018**: The agent MUST maintain conversation context to remember preferences, selected companies, and in-progress actions within a session.
- **FR-019**: The agent MUST present options clearly and summarize intended actions before making any changes on the customer's behalf.
- **FR-020**: The agent MUST support pagination across all list endpoints, allowing customers to navigate through results.

### Key Entities

- **Company**: A registered service provider with a public profile, service catalog, rating, and reviews. Companies offer services such as Moving, Cleaning, Disposal, Storage, Transport, Packing, and Unpacking.
- **Customer**: An authenticated user connected to one or more companies. Has a profile, can submit service requests, receive and manage offers, and write reviews.
- **Lead**: A potential customer who can be connected to multiple companies. Has a personal profile that pre-fills into future customer records. Connection statuses: Pending, Accepted, Rejected.
- **Service Request**: A customer's inquiry submitted to a specific company, containing preferred date, origin/destination addresses, and notes. Statuses: Pending, Declined, OfferSent, Closed.
- **Offer**: A company's response to a service request, containing service line items and pricing. Customers can accept (with digital signature and payment method) or reject (with reason). Statuses: Pending, Sent, Accepted, Rejected, Canceled.
- **Review**: A customer's rating and optional text feedback for a company. Subject to content moderation. One review per customer per company, updatable and deletable.
- **Digital Signature**: A unique customer identifier in format SIG-XXXXX-XXXXX, required for offer acceptance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Customers can discover and compare service companies within 2 conversational turns (one to describe their need, one to see results).
- **SC-002**: Customers can submit a complete service request within 4 conversational turns (need description, company selection, detail gathering, confirmation).
- **SC-003**: Customers can review, accept, or reject an offer within 3 conversational turns (list offers, view details, execute action with confirmation).
- **SC-004**: The agent correctly handles 100% of documented error codes with user-friendly explanations rather than raw error messages.
- **SC-005**: The agent never executes a state-changing action without explicit customer confirmation in the preceding turn.
- **SC-006**: 90% of customer intents are resolved without requiring the customer to rephrase or repeat information.
- **SC-007**: The agent correctly distinguishes between public (no-auth) and authenticated endpoints, never prompting for login on public actions.
- **SC-008**: Customers can complete their first end-to-end flow (discover company → submit request) within 5 minutes of starting a conversation.

## Assumptions

- The Wasla CRM API is available and stable at the documented base URL.
- JWT-based authentication is already implemented and tokens are provided to the agent at session start or via a login flow outside the agent's scope.
- The digital signature for each customer is pre-generated and known to the customer; the agent does not generate signatures.
- Content moderation for reviews is handled server-side; the agent does not perform client-side content filtering.
- Service types are a known finite set (Moving, Cleaning, Disposal, Storage, Transport, Packing, Unpacking) but the agent should handle any value the API returns.
- Stripe payment flow (checkout URL redirect and webhook confirmation) is handled outside the agent's direct control; the agent's role is to present the checkout URL and explain the process.
- Pagination defaults (pageSize of 10-12) are appropriate for conversational presentation; the agent can adjust based on context.
- The agent operates within a single customer's session and does not support multi-user or admin operations.
