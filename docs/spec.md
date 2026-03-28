# Product Specification: Job Discovery & Application Tracking Platform

## 1. Product Context

This product is a web-based system designed to help users systematically discover, track, and manage job opportunities—initially focused on machine learning and AI roles.

Instead of manually browsing multiple company websites, the system aggregates job postings from selected companies, keeps them up to date, and presents them in a unified interface. The user can define personalized views (filters), track which jobs they have applied to, and monitor their overall job search progress.

The system also includes a backend data pipeline responsible for discovering companies, extracting job listings from their career pages, and maintaining an up-to-date database.

The product has two main dimensions:

* **Data ingestion and normalization (backend pipelines)**
* **User interaction and tracking (frontend dashboard + API)**

---

## 2. User Flow Overview

A typical user journey looks like this:

1. The system continuously discovers and maintains a list of companies.
2. It periodically fetches job postings from those companies.
3. The user opens the dashboard and sees available jobs.
4. The user creates a “view” (e.g., *ML Engineer in Canada, Remote*).
5. The user browses jobs within that view.
6. The user clicks a job → goes to the company site → applies.
7. The user marks the job as “applied” in the dashboard.
8. The user later checks the summary page to track progress.

---

## 3. Frontend Pages

### 3.1 Dashboard Page (Core Product Surface)

The dashboard is the central interface of the application. It displays job opportunities aggregated from all companies and allows the user to browse, filter, and interact with them.

The purpose of this page is to replace fragmented job searching with a single, structured interface.

Each job is presented as a card (or table row) with essential information and quick actions.

Key behaviors:

* The user can quickly scan jobs
* The user can filter results dynamically
* The user can mark jobs as applied
* The user can navigate to the original job posting

Core features:

* Display list of jobs (card view + table view)
* Filters:

  * Job title keywords
  * Location
  * Remote / hybrid / onsite
  * Company
  * Date posted
* Sorting (e.g., newest first)
* Pagination or infinite scroll

Each job item includes:

* Title
* Company name
* Location
* Short description preview
* Tags (remote, type, etc.)
* Button: “Open job” (external link)
* Checkbox: “Applied”

Optional (future):

* Bookmark / hide job
* Inline notes preview

---

### 3.2 Job Detail Drawer / Page

When a user selects a job, they should be able to see more detailed information without losing context.

This can be implemented as a drawer or a dedicated page.

Purpose:
Provide full job context before applying.

Content:

* Full job description
* Company metadata
* Link to original posting
* Application tracking controls

Actions:

* Mark as applied
* Update application status
* Add notes
* Set follow-up reminder

---

### 3.3 Saved Views Page

This page allows users to create and manage reusable filters.

Instead of reapplying filters every time, users can define named “views” such as:

* “ML Engineer Remote”
* “Canada AI Jobs”
* “Applied Jobs”

Each view represents a saved query over the job dataset.

Purpose:
Enable efficient reuse of complex filters.

Features:

* Create new view
* Edit existing view
* Delete view
* Select a view to apply filters to dashboard

Each view contains:

* Name
* Filter definition (JSON)
* Sort configuration

---

### 3.4 Summary / Analytics Page

This page provides a high-level overview of the user’s job search activity.

The purpose is to give visibility into progress and outcomes.

Metrics displayed:

* Total jobs available
* Jobs in saved views
* Jobs applied to
* Application rate
* Applications over time

Optional enhancements:

* Funnel visualization (applied → interview → offer)
* Per-company breakdown

---

### 3.5 Admin Panel

This is an internal-facing interface for managing the system.

It is used to control data ingestion and ensure quality.

Purpose:
Allow operators to manage companies, monitor pipelines, and resolve issues.

Sections:

#### Companies Management

* View all companies
* Add/edit companies
* Set careers URL
* Enable/disable company
* Trigger manual sync

#### Jobs Inspection

* View jobs per company
* Inspect raw data
* Debug parsing issues

#### Pipeline Monitoring

* View sync runs
* See failures and logs
* Inspect metrics

---

## 4. Backend System Context

The backend is responsible for two distinct concerns:

1. Serving the application (API layer)
2. Maintaining data (pipeline layer)

These must remain logically separate.

---

## 5. Company Discovery System

The system maintains its own internal company registry.

There is no single global registry, so the system aggregates from multiple sources:

* OpenCorporates
* Registraire des entreprises du Québec
* Corporations Canada
* GLEIF

These are used as enrichment sources, not as authoritative truth.

### Company Lifecycle

A company progresses through states:

* discovered → found via registry/search
* enriched → domain and careers page identified
* validated → careers page confirmed working
* active → included in job sync
* disabled → excluded

Only **active companies** are used for job ingestion.

---

## 6. Job Ingestion System

This is the most critical backend component.

It is responsible for:

* Fetching jobs from company career sites
* Normalizing job data
* Deduplicating entries
* Tracking lifecycle changes

### Pipeline Behavior

* Runs on a schedule (e.g., every few hours)
* Processes companies in parallel
* Uses source-specific adapters

### Adapters

Each career site type is handled by an adapter:

* Greenhouse
* Lever
* Generic HTML fallback

Each adapter:

* Fetches jobs
* Parses structured data
* Outputs normalized job objects

---

### Job Lifecycle

Jobs are never deleted.

Instead:

* New jobs → inserted
* Existing jobs → updated
* Missing jobs → marked closed after N cycles

---

## 7. Application Tracking Model

Tracking applications is a core user feature.

This is modeled as a relationship between user and job.

A job is not globally “applied”—it is applied per user.

User actions:

* Mark job as applied
* Update status (interview, offer, etc.)
* Add notes
* Track follow-ups

---

## 8. API Layer

The backend exposes REST endpoints for:

Jobs:

* Retrieve filtered jobs
* Retrieve job details

Views:

* CRUD operations for saved views

Applications:

* Update application status

Admin:

* Manage companies
* Trigger syncs
* View pipeline runs

---

## 9. Non-Functional Requirements

Reliability:

* Pipelines must be idempotent
* No duplicate jobs

Performance:

* Indexed queries
* Pagination required

Observability:

* Log all pipeline runs
* Store error states

Scalability:

* Parallel job fetching
* Queue-friendly design

---

## 10. Implementation Phases

Phase 1 (MVP):

* Manual company entry
* Basic job ingestion (1 adapter)
* Dashboard
* Applied tracking

Phase 2:

* Saved views
* Summary page
* Admin panel

Phase 3:

* Multi-registry ingestion
* Additional adapters
* Observability improvements

---

## 11. Final Clarification

This product is not just a job board.

It is:

* A **job aggregation system**
* A **personal job tracking tool**
* A **data pipeline for structured job intelligence**

The frontend is relatively straightforward.

The core engineering complexity lies in:

* Reliable job ingestion
* Company normalization
* Data consistency over time
