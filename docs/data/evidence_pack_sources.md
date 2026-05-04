# TicketPilot Phase 7 Evidence Pack Sources

## Purpose

TicketPilot Phase 7 uses public and open customer-service-related datasets as reference material for scenario coverage, wording patterns, issue categories, and ticket-like structures.

The final TicketPilot evaluation dataset is **not** a raw copy of any single public dataset. It is a manually adapted synthetic Chinese support-ticket dataset designed for evaluating TicketPilot's workflow capabilities — intent classification, risk triage, evidence retrieval, no-evidence fallback, draft-only behavior, and human-review routing.

## Source usage policy

TicketPilot uses external datasets in three ways:

1. **Scenario reference** — Used to understand common customer-service issue types. Raw records are not copied directly into the repo.

2. **Wording reference** — Used to observe how users phrase complaints, refund requests, account issues, and support needs. Final tickets are manually rewritten into single-turn Chinese support tickets.

3. **Schema reference** — Used to design ticket fields, labels, priorities, and category coverage. TicketPilot-specific golden expectations are manually annotated.

## Source registry

| Source | Type | Language | Original task | TicketPilot usage | Raw data committed? | License / access note | Limitations |
|---|---|---|---|---|---|---|---|
| [CSDS](https://github.com/CSDS) — Chinese Customer Service Dialogue Summarization | Customer service dialogue summarization | Chinese | Dialogue summarization with overall/user/agent summaries | Reference for Chinese customer-service issue wording and scenario structure | No | Public research dataset; license/access must be checked before raw redistribution | Dialogue format, not single-turn ticket format; multiple turns per example |
| [Kaggle Customer Support Ticket Dataset](https://www.kaggle.com/) | Customer support tickets | English | Ticket analysis / classification | Reference for ticket fields, categories, and support workflow structure | No | Kaggle dataset; license must be checked per dataset page | English; not Chinese ecommerce-specific |
| [Kaggle Customer IT Support Ticket Dataset](https://www.kaggle.com/) | IT support tickets | English / multilingual | IT helpdesk support tickets | Reference for ticket-like issue descriptions and priority/category structure | No | Kaggle dataset; license must be checked per dataset page | IT support domain differs from ecommerce after-sales |
| [Chinese Chatbot Corpus](https://github.com/chatopera/chatbot-corpus) | Open Chinese dialogue corpus collection | Chinese | General dialogue across multiple sub-sources (Douban, Weibo, Tieba, etc.) | Limited reference for informal Chinese expression only | No | Repository uses Apache-2.0, but sub-source redistribution should be treated cautiously | Not customer-service-specific; aggregates multiple sub-corpora with varied original licenses |
| Public after-sales policy pages (e.g., e-commerce platform return/refund/privacy/payment policies) | Public policy text | Chinese | N/A — published platform policy | Manually rewritten into synthetic FAQ / Policy / Case knowledge records | No direct copy | Use only short transformed summaries, not raw copied policy pages | Policies differ by platform/company; may become outdated |

## Dataset adaptation rule

Raw public records are **not** directly treated as TicketPilot evaluation tickets. Each final ticket must be manually rewritten into a synthetic single-turn customer support ticket.

Each adapted ticket should include:
- `ticket_id`
- `original_text`
- `issue_type`
- risk scenario, if any
- expected evidence doc types
- expected human review behavior
- `source_reference_category`

## Non-goals

This evidence pack does not claim:
- real enterprise deployment;
- real customer data validation;
- production benchmark performance;
- real semantic retrieval effectiveness before Phase 8;
- automated customer reply sending.
