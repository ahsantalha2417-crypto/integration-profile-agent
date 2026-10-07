# Integration Profile Agent

A small prototype of an AI-assisted integration pipeline: it reads a partner's API
documentation, uses Claude to pull out what an engineer needs before building an
integration, and saves it as a structured **integration profile**. A collection of
profiles acts as a context layer, a single source of truth for every partner.

It also ranks an integration backlog and tracks the pipeline metrics that tell you
whether the process is working.

## What a profile captures

- Category, base URL, API style (REST, GraphQL, ...)
- Auth model and details (OAuth scopes, API keys, ...)
- Key endpoints for customers, orders, products and events
- Webhook support, rate limits
- Sandbox availability and how to get one
- Whether a partner program is required, where to sign up, approval notes
- **Open questions**: anything the docs don't answer. The model is told to flag gaps
  instead of guessing.
- Tracking fields maintained by the team: access status, request and approval dates

Claude answers through a forced tool call whose input schema is generated from the
Pydantic model, so every profile is valid, typed JSON.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key
# optional: export CLAUDE_MODEL=<model id>   (defaults to claude-sonnet-4-5)
```

## Usage

```bash
# Build a profile from a docs page
python -m integration_agent profile --partner Shopify --url https://shopify.dev/docs/api/admin-rest

# Or from a saved docs file
python -m integration_agent profile --partner Acme --file acme_docs.txt

# Rank the backlog and show metrics
python -m integration_agent backlog examples/backlog.csv
```

Profiles are saved to `profiles/<partner>.json`. Edit `access_status`,
`access_requested_on` and `access_granted_on` as partner approvals come through.

## Prioritization

```
score = 2 x customer_requests + 3 x strategic_fit - 2 x est_effort  (+5 if build-ready)
```

A partner is **build-ready** when access is approved (or not needed), the auth model
is known and key endpoints are documented.

## Metrics

- Backlog coverage: share of backlog partners with a profile
- Build-ready count
- Median days from access request to approval
- Open questions outstanding

## Tests

```bash
python -m pytest
```

The tests use a fake Claude client, so they run without an API key.

## Next steps

- Agent loop that follows links from a docs landing page to the auth, rate limit and
  webhook pages before extracting
- Re-check profiles on a schedule and flag changes to a partner's API
- Draft partner program applications from a profile for a human to review
