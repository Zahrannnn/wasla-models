# Customer Portal API - Agent-Friendly Documentation

> **For AI Chatbot Developers**: This document is designed to help you build an agentic AI chatbot that can assist users with the Customer Portal API. It includes system instructions, tool definitions, conversation examples, and decision-making guidelines.

---

## Table of Contents

1. [System Instructions for AI Agent](#1-system-instructions-for-ai-agent)
2. [Tool Definitions (Function Calling)](#2-tool-definitions-function-calling)
3. [Decision Tree: Which Tool to Use](#3-decision-tree-which-tool-to-use)
4. [User Flows & Conversation Examples](#4-user-flows--conversation-examples)
5. [Tool Details & Usage](#5-tool-details--usage)
6. [Error Handling Guide](#6-error-handling-guide)
7. [Best Practices](#7-best-practices)

---

## 1. System Instructions for AI Agent

### Role
You are a helpful AI assistant that helps users interact with the Customer Portal API. You can help users:
- Browse and discover service companies
- Manage their account (register, login, profile)
- Submit and manage reviews
- Create and manage service requests
- View and respond to offers

### User Types
1. **Guest User** - Not logged in, can only browse companies
2. **Lead User** - Registered but not accepted by any company
3. **Customer User** - Accepted by a company, full access to features

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Lead** | A user who registered but hasn't been accepted by any company yet |
| **Customer** | A user who has been accepted by at least one company |
| **Digital Signature** | A unique signature auto-generated at registration, required to accept offers |
| **Service Request** | An inquiry submitted to a company for services |
| **Offer** | A quote/proposal sent by a company to a customer |
| **Review** | Customer feedback for a company (1-5 stars + text) |

### Authentication Flow

```
Guest User
    │
    ├──► Register → Creates Lead account + Digital Signature
    │
    └──► Login → Returns JWT with user claims
                      │
                      ├── leadId only → Lead User (browse + create service requests)
                      │
                      └── customerId present → Customer User (full access)
```

### Important Rules

1. **Always check authentication state** before suggesting actions
2. **Public endpoints** (companies, reviews) don't require authentication
3. **Protected endpoints** require a valid JWT token in the Authorization header
4. **Offer acceptance** requires the user's digital signature (get it via `get_digital_signature`)
5. **Service requests** can be created by both Leads and Customers
6. **Reviews** can only be submitted by Customers (not Leads)

---

## 2. Tool Definitions (Function Calling)

Use these definitions to register tools with your AI framework (OpenAI Functions, Claude Tools, etc.):

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "register_customer",
        "description": "Register a new customer account. Creates a Lead record and generates a Digital Signature automatically. Call this when a new user wants to sign up.",
        "parameters": {
          "type": "object",
          "properties": {
            "email": {"type": "string", "description": "Valid email address (max 256 chars)"},
            "password": {"type": "string", "description": "Min 6 chars, must contain at least 1 digit"},
            "first_name": {"type": "string", "description": "User's first name (max 100 chars)"},
            "last_name": {"type": "string", "description": "User's last name (max 100 chars)"},
            "phone_number": {"type": "string", "description": "Optional phone number (max 50 chars)"}
          },
          "required": ["email", "password", "first_name", "last_name"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "login_customer",
        "description": "Authenticate a user and get JWT token. Returns user info including customerId/leadId to determine user type. Also returns Digital Signature needed for accepting offers.",
        "parameters": {
          "type": "object",
          "properties": {
            "email": {"type": "string", "description": "User's email address"},
            "password": {"type": "string", "description": "User's password"},
            "remember_me": {"type": "boolean", "description": "If true, extends refresh token to 30 days (default: 1 day)"}
          },
          "required": ["email", "password"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "refresh_token",
        "description": "Get a new access token using refresh token. Use this when the current token is expired or about to expire. Each refresh token can only be used once (token rotation).",
        "parameters": {
          "type": "object",
          "properties": {
            "refresh_token": {"type": "string", "description": "The refresh token from login response"}
          },
          "required": ["refresh_token"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "logout",
        "description": "Log out the current session by revoking the refresh token. The client should discard the access token after this.",
        "parameters": {
          "type": "object",
          "properties": {
            "refresh_token": {"type": "string", "description": "The refresh token to revoke"}
          },
          "required": ["refresh_token"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "logout_all",
        "description": "Log out from ALL devices by revoking all refresh tokens. Requires authentication."
      }
    },
    {
      "type": "function",
      "function": {
        "name": "list_companies",
        "description": "Browse and search companies on the platform. No authentication required. Great for showing users available service providers.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 12)"},
            "search": {"type": "string", "description": "Search by company name"},
            "service_type": {"type": "string", "description": "Filter by service type (e.g., 'Cleaning', 'Moving')"},
            "sort_by": {"type": "string", "description": "Sort by: 'rating', 'name', 'newest' (default: 'rating')"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_recommended_companies",
        "description": "Get AI-ranked company recommendations based on reviews, ratings, and recency. No authentication required. Best for 'Find me the best company' requests.",
        "parameters": {
          "type": "object",
          "properties": {
            "service_type": {"type": "string", "description": "Filter by service type"},
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_trending_companies",
        "description": "Get companies with improving recent reviews (last 90 days). Requires at least 2 recent reviews and 0.5+ star improvement. Great for 'Hot new companies' or 'Companies on the rise' requests.",
        "parameters": {
          "type": "object",
          "properties": {
            "service_type": {"type": "string", "description": "Filter by service type"},
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_company_details",
        "description": "Get detailed information about a specific company including contact info, services offered, and recent reviews. No authentication required.",
        "parameters": {
          "type": "object",
          "properties": {
            "company_id": {"type": "integer", "description": "The company's numeric ID"}
          },
          "required": ["company_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_company_reviews",
        "description": "Get paginated customer reviews for a company. Shows rating distribution and individual reviews. No authentication required.",
        "parameters": {
          "type": "object",
          "properties": {
            "company_id": {"type": "integer", "description": "The company's numeric ID"},
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
            "sort_by": {"type": "string", "description": "Sort by: 'newest', 'highest-rated' (default: 'newest')"}
          },
          "required": ["company_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "submit_review",
        "description": "Submit a new review for a company. Requires Customer authentication. Review text is moderated for inappropriate content. Only one review per customer per company allowed.",
        "parameters": {
          "type": "object",
          "properties": {
            "company_id": {"type": "integer", "description": "The company's numeric ID"},
            "rating": {"type": "integer", "description": "Star rating 1-5 (required)"},
            "review_text": {"type": "string", "description": "Review text, max 2000 chars (optional)"}
          },
          "required": ["company_id", "rating"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_review",
        "description": "Update an existing review. Only the customer who created the review can update it. Review text is moderated.",
        "parameters": {
          "type": "object",
          "properties": {
            "company_id": {"type": "integer", "description": "The company's numeric ID"},
            "rating": {"type": "integer", "description": "Updated star rating 1-5"},
            "review_text": {"type": "string", "description": "Updated review text, max 2000 chars"}
          },
          "required": ["company_id", "rating"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "delete_review",
        "description": "Delete the customer's own review for a company. This action cannot be undone.",
        "parameters": {
          "type": "object",
          "properties": {
            "company_id": {"type": "integer", "description": "The company's numeric ID"}
          },
          "required": ["company_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_my_reviews",
        "description": "Get all reviews written by the authenticated customer across all companies.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_customer_profile",
        "description": "Get the authenticated customer's profile. Only works if user has been accepted by a company (has customerId). Use get_lead_profile for Lead users.",
        "parameters": {"type": "object", "properties": {}}
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_customer_profile",
        "description": "Update the authenticated customer's profile. Email cannot be changed through this endpoint.",
        "parameters": {
          "type": "object",
          "properties": {
            "first_name": {"type": "string", "description": "First name (required)"},
            "last_name": {"type": "string", "description": "Last name (required)"},
            "phone_number": {"type": "string", "description": "Phone number"},
            "address": {"type": "string", "description": "Street address"},
            "city": {"type": "string", "description": "City"},
            "zip_code": {"type": "string", "description": "Zip/Postal code"},
            "country": {"type": "string", "description": "Country"}
          },
          "required": ["first_name", "last_name"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_lead_profile",
        "description": "Get the lead's profile including list of connected companies (accepted, pending). Use this for users who registered but haven't been accepted by any company yet.",
        "parameters": {"type": "object", "properties": {}}
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_lead_profile",
        "description": "Update the lead's profile. Changes will be pre-filled when the lead becomes a customer.",
        "parameters": {
          "type": "object",
          "properties": {
            "first_name": {"type": "string", "description": "First name (required)"},
            "last_name": {"type": "string", "description": "Last name (required)"},
            "phone_number": {"type": "string", "description": "Phone number"},
            "address": {"type": "string", "description": "Street address"},
            "city": {"type": "string", "description": "City"},
            "zip_code": {"type": "string", "description": "Zip/Postal code"},
            "country": {"type": "string", "description": "Country"}
          },
          "required": ["first_name", "last_name"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_digital_signature",
        "description": "Get the user's digital signature after password verification. The digital signature is required to accept offers. IMPORTANT: Requires password re-verification for security.",
        "parameters": {
          "type": "object",
          "properties": {
            "password": {"type": "string", "description": "User's current password to verify identity"}
          },
          "required": ["password"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_my_offers",
        "description": "Get all offers (quotes) sent to the customer by companies. Shows offer status, amounts, and company info.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page, max 50 (default: 10)"},
            "status": {"type": "string", "description": "Filter by status: 'Pending', 'Sent', 'Accepted', 'Rejected', 'Canceled'"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_offer_details",
        "description": "Get detailed information about a specific offer including service line items, locations, insurance info, and pricing breakdown.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "The offer's numeric ID"}
          },
          "required": ["offer_id"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "accept_offer",
        "description": "Accept an offer. Requires the user's digital signature. Can choose COD (Cash on Delivery) or Online (Stripe) payment. For online payment, returns a Stripe checkout URL.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "The offer's numeric ID"},
            "digital_signature": {"type": "string", "description": "User's digital signature (get via get_digital_signature)"},
            "payment_method": {"type": "string", "description": "Payment method: 'COD' or 'Online'"}
          },
          "required": ["offer_id", "digital_signature", "payment_method"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "reject_offer",
        "description": "Reject an offer. Must provide a reason for rejection.",
        "parameters": {
          "type": "object",
          "properties": {
            "offer_id": {"type": "integer", "description": "The offer's numeric ID"},
            "rejection_reason": {"type": "string", "description": "Reason for rejection (max 2000 chars)"}
          },
          "required": ["offer_id", "rejection_reason"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_dashboard",
        "description": "Get dashboard summary showing total offers, offers by status, total reviews, and recent activity. Great for home screen or summary view.",
        "parameters": {"type": "object", "properties": {}}
      }
    },
    {
      "type": "function",
      "function": {
        "name": "create_service_request",
        "description": "Submit a service inquiry to a company. Can be done by both Lead and Customer users. Creates a Customer record if the user is a Lead. This is how users request services from companies.",
        "parameters": {
          "type": "object",
          "properties": {
            "company_id": {"type": "integer", "description": "The company's numeric ID (required)"},
            "service_type": {"type": "string", "description": "Type of service (e.g., 'Moving', 'Cleaning') (required)"},
            "from_street": {"type": "string", "description": "Origin street address"},
            "from_city": {"type": "string", "description": "Origin city"},
            "from_zip_code": {"type": "string", "description": "Origin zip code"},
            "from_country": {"type": "string", "description": "Origin country"},
            "to_street": {"type": "string", "description": "Destination street address"},
            "to_city": {"type": "string", "description": "Destination city"},
            "to_zip_code": {"type": "string", "description": "Destination zip code"},
            "to_country": {"type": "string", "description": "Destination country"},
            "preferred_date": {"type": "string", "description": "Preferred service date (YYYY-MM-DD)"},
            "preferred_time_slot": {"type": "string", "description": "Preferred time (e.g., 'Morning 8am-12pm')"},
            "notes": {"type": "string", "description": "Additional notes or special instructions (max 2000 chars)"}
          },
          "required": ["company_id", "service_type"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_my_service_requests",
        "description": "Get all service requests submitted by the authenticated customer.",
        "parameters": {
          "type": "object",
          "properties": {
            "page_index": {"type": "integer", "description": "Page number (default: 1)"},
            "page_size": {"type": "integer", "description": "Items per page (default: 10)"},
            "status": {"type": "string", "description": "Filter by status: 'Pending', 'InProgress', 'Closed'"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_service_request_details",
        "description": "Get detailed information about a specific service request including location details, preferred dates, and any associated offer info.",
        "parameters": {
          "type": "object",
          "properties": {
            "service_request_id": {"type": "integer", "description": "The service request's numeric ID"}
          },
          "required": ["service_request_id"]
        }
      }
    }
  ]
}
```

---

## 3. Decision Tree: Which Tool to Use

### User Authentication Decisions

```
User wants to sign up?
    └─► YES → register_customer
    
User wants to log in?
    └─► YES → login_customer
    
Token expired?
    └─► YES → refresh_token (with stored refresh_token)
    
User wants to log out?
    └─► YES → logout (single device) or logout_all (all devices)
```

### Company Discovery Decisions

```
User wants to find companies?
    │
    ├─► "Best recommended" → get_recommended_companies
    │
    ├─► "Hot/trending" → get_trending_companies
    │
    ├─► "Search by name/type" → list_companies (with search/service_type)
    │
    └─► "Details of one company" → get_company_details (companyId known)
```

### Review Decisions

```
User wants to see reviews?
    └─► get_company_reviews (public, no auth needed)

User wants to write/update/delete their own review?
    └─► Requires Customer auth
        │
        ├─► Submit new → submit_review
        ├─► Update existing → update_review
        └─► Delete → delete_review

User wants to see their own reviews?
    └─► get_my_reviews
```

### Offer Decisions

```
User wants to see their offers?
    └─► get_my_offers (paginated, filterable by status)

User wants offer details?
    └─► get_offer_details (offerId known)

User wants to accept offer?
    └─► accept_offer
        │
        ├─► Need digital signature first → get_digital_signature (requires password)
        └─► Payment method: 'COD' or 'Online'

User wants to reject offer?
    └─► reject_offer (requires reason)
```

### Profile Decisions

```
User wants to view profile?
    ├─► Has customerId → get_customer_profile
    └─► Has only leadId → get_lead_profile

User wants to update profile?
    ├─► Customer user → update_customer_profile
    └─► Lead user → update_lead_profile
```

### Service Request Decisions

```
User wants to request a service?
    └─► create_service_request
        └─► Can be Lead or Customer

User wants to see their service requests?
    └─► get_my_service_requests

User wants details of one request?
    └─► get_service_request_details
```

---

## 4. User Flows & Conversation Examples

### Flow 1: New User Registration

**Conversation:**
> **User:** I want to create an account
> **AI:** I'd be happy to help you register! I'll need a few details:
> - Email address
> - Password (min 6 characters with at least 1 number)
> - First name and last name
> - Phone number (optional)
> 
> What would you like to use?

> **User:** email: john@example.com, password: Pass123, first: John, last: Doe
> **AI:** *(calls register_customer)*
> 
> Your account has been created successfully! 🎉
> 
> **Your account details:**
> - **Name:** John Doe
> - **Email:** john@example.com
> - **Digital Signature:** DS-2026-ABC123XYZ
> 
> You're now logged in as a **Lead**. Once a company accepts your service request, you'll become a **Customer** with full access to offers and reviews.
> 
> What would you like to do next?

---

### Flow 2: Finding and Requesting Services

**Conversation:**
> **User:** I'm looking for a moving company
> **AI:** *(calls list_companies with service_type: "Moving")*
> 
> Here are moving companies available on our platform:
> 
> 1. **Acme Movers** - ⭐ 4.3 (15 reviews)
>    - Professional Moving: from CHF 800
> 2. **Swift Move AG** - ⭐ 4.7 (28 reviews)
>    - Full Service Moving, Packing
> 3. **Budget Transport** - ⭐ 3.9 (42 reviews)
>    - Economy Moving
> 
> Would you like more details on any of these, or would you like to submit a service request?

> **User:** Tell me more about Acme Movers
> **AI:** *(calls get_company_details with company_id: 1)*
> *(calls get_company_reviews with company_id: 1)*
> 
> **Acme Movers**
> 📍 Bahnhofstrasse 1, Zürich, Switzerland
> 📞 +41 44 123 4567
> ✉️ info@acme.test
> ⭐ 4.3 average (15 reviews)
> 
> **Services:**
> - **Professional Moving**: CHF 800-3000 per move
> - **Packing Service**: Additional
> 
> **Recent Reviews:**
> - ⭐⭐⭐⭐⭐ Jane: "Excellent service, very professional team."
> - ⭐⭐⭐⭐⭐ Michael: "Fast and careful with our belongings."
> 
> Would you like to request a service from Acme Movers?

> **User:** Yes, I need to move from Zurich to Bern on March 15th
> **AI:** *(calls create_service_request)*
> 
> ✅ **Service Request Submitted!**
> 
> **Reference:** SR-2026-001
> **Company:** Acme Movers
> **Service:** Moving
> **From:** Zürich
> **To:** Bern
> **Preferred Date:** March 15, 2026
> **Status:** Pending
> 
> Acme Movers will review your request and may send you an offer. You can track the status in your dashboard.
> 
> Is there anything else I can help you with?

---

### Flow 3: Managing Offers

**Conversation:**
> **User:** Check my offers
> **AI:** *(calls get_my_offers)*
> 
> You have **3 offers**:
> 
> | # | Company | Service | Amount | Status |
> |---|---------|---------|--------|--------|
> | 1 | Acme Movers | Moving | CHF 1,500 | Sent |
> | 2 | CleanPro | Cleaning | CHF 350 | Pending |
> | 3 | Swift Move | Moving | CHF 1,800 | Accepted |
> 
> Would you like to:
> - View details of any offer?
> - Accept or reject an offer?
> - Filter by status?

> **User:** I want to see details of offer #1
> **AI:** *(calls get_offer_details with offer_id: 101)*
> 
> **Offer Details - OFF-2026-001**
> 
> | Field | Value |
> |-------|-------|
> | **Company** | Acme Movers |
> | **Service** | Moving |
> | **Total** | CHF 1,500.00 |
> | **Discount** | CHF 100.00 |
> | **Issue Date** | Jan 20, 2026 |
> 
> **Locations:**
> - 📍 From: Alte Strasse 1, 8001 Zürich
> - 📍 To: Neue Strasse 5, 3000 Bern
> 
> **Service Breakdown:**
> - Moving: CHF 1,200
> - Packing: CHF 300
> 
> **Included:**
> - Insurance: Transport insurance included
> - What's covered: Loading, transport, unloading
> - VAT: Included in price
> 
> 📄 PDF: [Download Offer](link)
> 
> Would you like to accept or reject this offer?

> **User:** I want to accept it
> **AI:** To accept this offer, I'll need your digital signature for verification. This is a security measure required for all offer acceptances.
> 
> Could you confirm your password to retrieve your digital signature?

> **User:** My password is Pass123
> **AI:** *(calls get_digital_signature with password: "Pass123")*
> 
> ✓ Signature verified!
> 
> How would you like to pay?
> - **COD (Cash on Delivery)**: Pay when the service is delivered
> - **Online (Stripe)**: Pay now via credit card
> 
> Which option would you prefer?

> **User:** COD is fine
> **AI:** *(calls accept_offer with offer_id: 101, digital_signature: "DS-2026-ABC123XYZ", payment_method: "COD")*
> 
> ✅ **Offer Accepted Successfully!**
> 
> **Offer:** OFF-2026-001
> **Company:** Acme Movers
> **Payment:** Cash on Delivery
> 
> Acme Movers will be in touch to confirm the moving date. You can track this in your offers section.
> 
> Is there anything else I can help you with?

---

### Flow 4: Submitting a Review

**Conversation:**
> **User:** I want to leave a review for Acme Movers
> **AI:** Great! I can help you submit a review for Acme Movers.
> 
> Please provide:
> - **Star rating** (1-5 stars, where 5 is excellent)
> - **Review text** (optional, max 2000 characters)
> 
> What rating would you give?

> **User:** 5 stars, and the text: "Great service, very careful with fragile items!"
> **AI:** *(calls submit_review with company_id: 1, rating: 5, review_text: "Great service, very careful with fragile items!")*
> 
> ✅ **Review Submitted Successfully!**
> 
> | Field | Value |
> |-------|-------|
> | **Company** | Acme Movers |
> | **Rating** | ⭐⭐⭐⭐⭐ (5/5) |
> | **Your Review** | "Great service, very careful with fragile items!" |
> | **Posted** | Feb 11, 2026 |
> 
> Thank you for your feedback! Your review helps other customers make informed decisions.
> 
> Is there anything else I can help you with?

---

### Flow 5: Dashboard Overview

**Conversation:**
> **User:** Show me my dashboard
> **AI:** *(calls get_dashboard)*
> 
> **📊 Your Dashboard**
> 
> **Offers Overview:**
> | Status | Count |
> |--------|-------|
> | Pending | 1 |
> | Sent | 2 |
> | Accepted | 1 |
> | Rejected | 1 |
> 
> **Total Offers:** 5
> 
> **Reviews:** You have submitted 3 reviews
> 
> **Recent Activity:**
> - 📋 Offer from Acme Movers (Moving) - CHF 1,500 - Status: Sent
> - 📋 Offer from CleanPro (Cleaning) - CHF 350 - Status: Pending
> - ⭐ Review posted for Acme Movers
> 
> Is there anything specific you'd like to do?

---

## 5. Tool Details & Usage

### Authentication Tools

| Tool | When to Use | Auth Required |
|------|-------------|---------------|
| `register_customer` | New user signup | No |
| `login_customer` | User login | No |
| `refresh_token` | Token expired | No (uses refresh token) |
| `logout` | User logout (single device) | No (uses refresh token) |
| `logout_all` | User logout (all devices) | Yes |

### Company Discovery Tools

| Tool | When to Use | Auth Required |
|------|-------------|---------------|
| `list_companies` | Browse/search companies | No |
| `get_recommended_companies` | AI-ranked recommendations | No |
| `get_trending_companies` | Hot/improving companies | No |
| `get_company_details` | Single company info | No |
| `get_company_reviews` | Company reviews list | No |

### Review Tools

| Tool | When to Use | Auth Required |
|------|-------------|---------------|
| `submit_review` | Write new review | Yes (Customer) |
| `update_review` | Edit own review | Yes (Customer) |
| `delete_review` | Remove own review | Yes (Customer) |
| `get_my_reviews` | View own reviews | Yes (Customer) |

### Profile Tools

| Tool | When to Use | Auth Required |
|------|-------------|---------------|
| `get_customer_profile` | View customer profile | Yes (Customer) |
| `update_customer_profile` | Edit customer profile | Yes (Customer) |
| `get_lead_profile` | View lead profile | Yes (Lead) |
| `update_lead_profile` | Edit lead profile | Yes (Lead) |
| `get_digital_signature` | Get signature (needs password) | Yes |

### Offer Tools

| Tool | When to Use | Auth Required |
|------|-------------|---------------|
| `get_my_offers` | List all offers | Yes (Customer) |
| `get_offer_details` | Single offer details | Yes (Customer) |
| `accept_offer` | Accept an offer | Yes (Customer) |
| `reject_offer` | Reject an offer | Yes (Customer) |
| `get_dashboard` | Dashboard summary | Yes (Customer) |

### Service Request Tools

| Tool | When to Use | Auth Required |
|------|-------------|---------------|
| `create_service_request` | Submit inquiry | Yes (Customer or Lead) |
| `get_my_service_requests` | List own requests | Yes (Customer) |
| `get_service_request_details` | Single request details | Yes (Customer) |

---

## 6. Error Handling Guide

### HTTP Status Codes

| Code | Meaning | What to Tell User |
|------|---------|------------------|
| 200 | Success | Operation completed |
| 201 | Created | Resource created successfully |
| 204 | No Content | Operation succeeded (logout, delete) |
| 400 | Bad Request | Invalid input - check error details |
| 401 | Unauthorized | Please log in again |
| 403 | Forbidden | You don't have permission for this |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Already exists (e.g., duplicate review) |
| 422 | Unprocessable | Business rule violation |
| 429 | Too Many Requests | Rate limited - try again later |
| 500 | Server Error | Something went wrong on our end |

### Common Error Scenarios

**Rate Limited (429)**
```
User: "I can't log in"
AI: "It looks like there were too many login attempts. Please wait about a minute and try again. This is a security measure to protect accounts."
```

**Invalid Credentials (401)**
```
User: "Login failed"
AI: "The email or password you entered is incorrect. Please double-check your credentials and try again. If you've forgotten your password, you can request a reset."
```

**Not a Customer Yet (403)**
```
User: "I want to submit a review"
AI: "Reviews can only be submitted by customers who have been accepted by a company. Have you submitted a service request to a company? Once they accept you as a customer, you'll be able to leave reviews."
```

**Company Not Found (404)**
```
User: "Show me company #999"
AI: "I couldn't find a company with ID 999. This company might not exist or may have been removed. Would you like to browse our available companies instead?"
```

**Already Reviewed (409)**
```
User: "Submit a review for Acme Movers"
AI: "You've already submitted a review for Acme Movers. Would you like to update your existing review instead?"
```

**Invalid Digital Signature (401)**
```
User: "Accept offer"
AI: "The digital signature you provided doesn't match our records. This might happen if you're trying to accept an offer with a different account. Please verify you're logged into the correct account."
```

**Content Moderation (400)**
```
User: "Submit review: [abusive content]"
AI: "I'm sorry, but your review couldn't be submitted because it contains inappropriate content. Please write a constructive review that follows our community guidelines."
```

---

## 7. Best Practices

### 1. Always Confirm Before Actions
Before calling destructive actions (delete, reject), confirm with the user:
```
AI: "Are you sure you want to delete your review for Acme Movers? This cannot be undone."
```

### 2. Guide Users to Authentication
When a user tries to access protected features without auth:
```
AI: "To access your offers and manage your account, you'll need to log in first. Would you like to log in or create a new account?"
```

### 3. Provide Context
When showing lists, summarize and let user choose:
```
AI: "I found 12 cleaning companies. Here are the top 3 by rating. Would you like to see more, or would you like details on any of these?"
```

### 4. Handle Pagination Gracefully
When results are paginated:
```
AI: "Showing the first 10 of 45 reviews. Would you like to see more?"
```

### 5. Validate Input Before Calling
Check user input matches requirements:
- Rating must be 1-5
- Password min 6 chars with digit
- Email must be valid format
- Dates should be in future for preferred dates

### 6. Explain What's Needed
When a tool requires additional info:
```
AI: "To submit a review, I need:
- A star rating (1-5 stars)
- The company ID (I can help you find this)
- Optionally, your review text

Which company would you like to review?"
```

### 7. Use Natural Language
Don't just dump JSON - explain in conversational terms:
```
Instead of: "{"status": "Sent", "totalAmount": 1500}"
Say: "This offer is awaiting your response. The total amount is CHF 1,500 with a CHF 100 discount."
```

### 8. Offer Next Steps
After completing an action:
```
AI: "Great! Your service request has been submitted. You can track its status in your dashboard. Is there anything else you'd like help with?"
```

### 9. Handle Partial Information
When user doesn't specify everything:
```
User: "I need to move"
AI: "I can help you create a service request! To get started, I'll need:
- Which company would you like to request from? (I can show you available moving companies)
- When do you need the service?
- Where are you moving from and to?

Would you like me to show you available moving companies first?"
```

### 10. Security Reminders
- Never log or expose tokens
- Remind users to keep passwords safe
- Explain why password is needed for digital signature retrieval
- Don't encourage sharing accounts

---

## Quick Reference: Common User Questions → Tool Mapping

| User Question | Tool to Use |
|---------------|-------------|
| "I want to sign up" | `register_customer` |
| "I want to log in" | `login_customer` |
| "Show me companies" | `list_companies` |
| "Find the best company" | `get_recommended_companies` |
| "Show trending companies" | `get_trending_companies` |
| "Company details" | `get_company_details` |
| "Show reviews" | `get_company_reviews` |
| "Write a review" | `submit_review` |
| "Edit my review" | `update_review` |
| "Delete my review" | `delete_review` |
| "Show my reviews" | `get_my_reviews` |
| "My profile" | `get_customer_profile` or `get_lead_profile` |
| "Update my info" | `update_customer_profile` or `update_lead_profile` |
| "Get my signature" | `get_digital_signature` |
| "Show my offers" | `get_my_offers` |
| "Offer details" | `get_offer_details` |
| "Accept offer" | `accept_offer` |
| "Decline offer" | `reject_offer` |
| "My dashboard" | `get_dashboard` |
| "Request service" | `create_service_request` |
| "My requests" | `get_my_service_requests` |
| "Request details" | `get_service_request_details` |

---

*Document Version: 1.0*  
*Last Updated: March 2026*
