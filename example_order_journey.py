"""Index one order journey, then retrieve the receipt for an agent tool call."""

from ecommerce_search import InfraiEmbedder, OrderDocument, OrderSearch


def main() -> None:
    search = OrderSearch(InfraiEmbedder())
    search.index(
        [
            OrderDocument("evt-101", "order-1042", "checkout", "Card accepted for 84 dollars."),
            OrderDocument("evt-102", "order-1042", "fulfillment", "Parcel handed to the carrier."),
            OrderDocument("evt-103", "order-1042", "receipt", "Receipt emailed after payment."),
            OrderDocument("evt-201", "order-2055", "receipt", "Receipt for a different customer order."),
        ]
    )
    hits = search.search("order-1042", "Where is my payment receipt?", limit=2)
    for hit in hits:
        print(f"{hit.kind}: {hit.text} (score={hit.score})")


if __name__ == "__main__":
    main()
