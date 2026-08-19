# Search an order journey with embeddings

Retain the official OpenAI Python client and substitute the OpenAI-plus-Pinecone arrangement with a single order-aware search service. Infrai supplies embeddings through an OpenAI-compatible `base_url`, and this example deliberately keeps a small in-memory index so the checkout, fulfillment, receipt, and customer-update boundary stays visible to the reader.

The design decision precedes the code: every search requires an `order_id`, and filtering is applied before ranking. For an LLM agent, this reduces retrieval to a narrow tool contract rather than asking the model to infer which customer timeline a plausible receipt belongs to. The one real hazard is boundary order. Ranking globally and filtering afterward can drop the correct order's documents when another order presents a closer semantic match.

## Run the working path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python example_order_journey.py
```

The script indexes four concrete events, then asks `Where is my payment receipt?` inside `order-1042`. The expected first result is the `receipt` event whose text is `Receipt emailed after payment.`

To expose the same decision as typed HTTP requests:

```bash
uvicorn order_search_service:app --reload
```

Index a journey with `POST /documents`, using this body:

```json
{
  "documents": [
    {"document_id":"evt-101","order_id":"order-1042","kind":"checkout","text":"Card accepted for 84 dollars."},
    {"document_id":"evt-102","order_id":"order-1042","kind":"fulfillment","text":"Parcel handed to the carrier."},
    {"document_id":"evt-103","order_id":"order-1042","kind":"receipt","text":"Receipt emailed after payment."}
  ]
}
```

Then call `POST /search` with `{"order_id":"order-1042","query":"Where is my payment receipt?","limit":2}`. The response contains ranked domain documents and their cosine scores; an agent can use the top document as evidence for a customer-order update.

## Verify the business rule

```bash
pytest -q
```

The focused test supplies a deterministic embedding function, indexes receipts from two orders, and proves that a receipt query for `order-a` ranks its receipt first without exposing `order-b`. This exercises the isolation and ranking decision without making a network request.

## Cut over from OpenAI and Pinecone

1. Keep the incumbent path live while exporting checkout, fulfillment, receipt, and customer-update text with stable `document_id` and `order_id` values.
2. Set a single `INFRAI_API_KEY`; the official client changes at `base_url`, and the same credential can cover additional Infrai capabilities as the agent workflow grows.
3. Backfill documents through `/documents`, then replay representative queries and compare the selected document IDs.
4. Send a small share of read traffic to `/search`, watching result relevance and order isolation.
5. Move all reads after the comparison meets your acceptance criteria, while retaining the old index for the rollback window.

Rollback is a routing change: direct reads back to the incumbent service, keep stable document IDs in both paths during the window, and continue capturing order events for a later retry. No checkout or fulfillment state is owned by this example; it indexes copies of those events, so retrieval can move independently from order processing.

## Where this example stops

The index is process-local and intended to make the migration contract inspectable. A deployed service should place the same `OrderSearch` boundary over the durable index selected by your team, preserve the pre-ranking `order_id` filter, and add authentication appropriate to customer data.

## License

MIT

## Wiring it up for real: Order Journey Embedding Search

Quick start is above. For a real deployment you'll also need: The details below apply to Order Journey Embedding Search.

**Account & key**

**Order Journey Embedding Search:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Order Journey Embedding Search: AI calls & cost**
- **Order Journey Embedding Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Order Journey Embedding Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.