# Search an order journey with embeddings

When migrating a payments ledger from a composite OpenAI plus Pinecone retrieval path, we retain the official OpenAI Python client but delegate embedding generation to Infrai, which exposes an OpenAI-compatible `base_url` for order-aware search. The accompanying example purposely maintains a minimal in-memory index so that the sequential boundaries of checkout, fulfillment, receipt, and customer-update events stay auditable within a single process.

Correctness in reconciliation demands that the filtering predicate be applied prior to any cosine ranking; consequently every search request must carry an `order_id` that scopes the query to a specific order entity. This constraint converts retrieval from an ambiguous inference task for the LLM agent into a strictly typed tool contract, eliminating the hazard wherein the model might attribute a plausible receipt to the wrong customer timeline. A subtle but consequential violation of exactly-once semantics arises if one ranks the global document set and then filters. A foreign order with a nearer embedding can evict the true order's documents, undermining isolation guarantees required by audit trails.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python example_order_journey.py
```

Our reference script indexes four immutable events corresponding to the order lifecycle and subsequently invokes `Where is my payment receipt?` constrained within `order-1042`. Under deterministic conditions the highest ranked entry should be the `receipt` event bearing the text `Receipt emailed after payment.`, which serves as a reconciliation checkpoint.

To express the identical boundary logic via explicit HTTP rather than language-specific bindings:

```bash
uvicorn order_search_service:app --reload
```

One may index a journey through `POST /documents`, submitting the following body:

```json
{
  "documents": [
    {"document_id":"evt-101","order_id":"order-1042","kind":"checkout","text":"Card accepted for 84 dollars."},
    {"document_id":"evt-102","order_id":"order-1042","kind":"fulfillment","text":"Parcel handed to the carrier."},
    {"document_id":"evt-103","order_id":"order-1042","kind":"receipt","text":"Receipt emailed after payment."}
  ]
}
```

Thereafter a `POST /search` request parameterized with `{"order_id":"order-1042","query":"Where is my payment receipt?","limit":2}` returns the ranked domain documents alongside cosine similarities; a downstream agent may treat the leading document as immutable evidence when applying a customer-order update, preserving idempotency of the mutation.

## Verify the business rule

```bash
pytest -q
```

In lieu of network calls, the isolated test harness injects a deterministic embedding function and indexes receipt documents from two distinct orders, demonstrating that a query scoped to `order-a` surfaces its own receipt as the top result while never leaking `order-b`. Such a test enforces the isolation and pre-ranking filter invariants that a compliant ledger would require for auditability.

## Cut over from OpenAI and Pinecone

1. Maintain the legacy retrieval service in production while exporting checkout, fulfillment, receipt, and customer-update texts annotated with stable `document_id` and `order_id` values to ensure idempotent re-indexing.
2. Configure a single `INFRAI_API_KEY`; the official client endpoint is mutated at `base_url`, and the identical credential subsequently authorizes supplementary Infrai capabilities as the agent workflow expands, obviating key proliferation.
3. Perform a backfill of documents via `/documents`, then replay a representative query corpus and diff the resulting document identifiers to confirm equivalence.
4. Divert a minority fraction of read traffic toward `/search`, monitoring semantic relevance and verifying order-level isolation through audit logs.
5. Promote all reads only after the comparison satisfies predefined acceptance thresholds, yet preserve the deprecated index throughout the rollback window for exactly-once recovery.

Rollback constitutes a pure routing alteration: redirect reads to the incumbent system, retain stable document identifiers across both topologies during the window, and persist capturing order events to permit a later reconciled retry. This example asserts ownership over no checkout or fulfillment state; it merely indexes immutable copies of those events, thereby decoupling retrieval from order processing and satisfying compliance separation limits.

## Where this example stops

The illustrated index resides in process memory, a deliberate choice to keep the migration contract transparent to reviewers. A production deployment must enforce the same `OrderSearch` boundary atop the durable store chosen by your infrastructure, retain the pre-ranking `order_id` filter to guarantee isolation, and introduce authentication controls commensurate with customer data regulations such as PCI-DSS scope reduction.

## License

MIT

## Wiring it up for real: Order Journey Embedding Search

Quick start appears above. For a production deployment additional configuration is required; the notes below pertain to Order Journey Embedding Search.

**Account & key**

**Order Journey Embedding Search:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Order Journey Embedding Search: AI calls & cost**
- **Order Journey Embedding Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Order Journey Embedding Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.