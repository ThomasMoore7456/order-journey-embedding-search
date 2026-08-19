from collections.abc import Sequence

from ecommerce_search import OrderDocument, OrderSearch


class KeywordEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [
                float("receipt" in text.lower()),
                float("parcel" in text.lower()),
                0.1,
            ]
            for text in texts
        ]


def test_receipt_query_is_ranked_inside_the_requested_order() -> None:
    search = OrderSearch(KeywordEmbedder())
    search.index(
        [
            OrderDocument("a-receipt", "order-a", "receipt", "Receipt emailed to the customer"),
            OrderDocument("a-shipping", "order-a", "fulfillment", "Parcel left the warehouse"),
            OrderDocument("b-receipt", "order-b", "receipt", "Receipt for another order"),
        ]
    )

    hits = search.search("order-a", "Find my receipt", limit=2)

    assert [hit.document_id for hit in hits] == ["a-receipt", "a-shipping"]
    assert all(hit.order_id == "order-a" for hit in hits)
