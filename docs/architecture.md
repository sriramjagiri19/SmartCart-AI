# Architecture and business decisions

1. Generate master entities first: Category, Customer, Product.
2. Generate dependent events: Session, PageView, Cart, CartLine, Order, OrderLine.
3. Derive ProductRelation from product pairs co-occurring in orders.
4. Derive recommendation eligibility from product lifecycle and inventory.
5. Assign session split by timestamp: before 2026-09-01 is train; on/after is test.
6. Keep deliberate anomalies labelled in a separate ground-truth file.
7. Compute line totals from quantity × unit price.
8. Evaluate recommendation output with offline Precision@K, Recall@K and catalog coverage.

## Recommendation policy

- Discontinued products are never eligible.
- Out-of-stock products are never eligible.
- Products already purchased by a customer are excluded.
- Customers without purchase history use a cold-start popularity/category fallback.
- Ground-truth anomaly labels are not used as recommendation features.

## Metric caveat

The generated data and offline metrics are synthetic demonstration outputs, not evidence of production business impact. Precision@K and Recall@K are calculated against held-out synthetic purchase outcomes and should be interpreted as a baseline.
