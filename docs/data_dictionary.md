# SmartCart AI — Data Dictionary

All data is synthetic. IDs are deterministic and immutable for a fixed seed and scale.

| Entity / file | Primary key | Important fields | Validation |
|---|---|---|---|
| Customer / customers.csv | customer_id | created_at, segment, is_active | CUS-######; segment in regular/new/high_value |
| Category / categories.csv | category_id | category_name, parent_category_id, is_seasonal | CAT-######; parent is optional and must exist |
| Product / products.csv | product_id | category_id, price, inventory_qty, product_status | SKU-######; price >= 0; status active/out_of_stock/discontinued |
| Session / sessions.csv | session_id | customer_id, started_at, ended_at, device, split | SES-2026-######; customer FK; end >= start |
| PageView / pageviews.csv | event_id | session_id, customer_id, product_id, event_time | EVT-{session-id}-###; all parent IDs must exist |
| Cart / carts.csv | cart_id | customer_id, session_id, created_at, cart_status | CART-2026-######; valid customer/session |
| CartLine / cart_lines.csv | cart_line_id | cart_id, product_id, quantity, unit_price, line_total | CL-######-##; quantity > 0; total = quantity × price |
| Order / orders.csv | order_id | customer_id, session_id, order_time, order_status | ORD-2026-######; session optional; status completed/cancelled |
| OrderLine / order_lines.csv | order_line_id | order_id, product_id, quantity, unit_price, line_total | OL-######-##; valid order/product; arithmetic reconciles |
| ProductRelation / product_relations.csv | relation_id | product_id, related_product_id, relation_type, strength, effective dates | REL-#######; two valid product references; effective_to optional |
| Recommendation / recommendations.csv | recommendation_id | customer_id, product_id, generated_at, score, model_version | REC-#######; - `score`: Positive weighted ranking score produced by the hybrid recommendation engine. Higher scores indicate stronger recommendation relevance. Scores are not normalized to the range [0, 1]. |

## Cardinality

- Customer 1:N Session, Cart, Order, Recommendation.
- Category 1:N Product; Category 1:N child Category through optional parent_category_id.
- Session 1:N PageView and 0:N Cart; Order has an optional Session.
- Cart 1:N CartLine; Order 1:N OrderLine.
- Product 1:N PageView, CartLine and OrderLine.
- Product N:M Product through ProductRelation (bridge-like relationship table).
- Customer N:M Product through Recommendation (recommendation records form the association).
- ProductRelation effective_to is blank for an open-ended relationship.

## Lifecycle states

- Product: active, out_of_stock, discontinued.
- Cart: active, converted, abandoned.
- Order: completed, cancelled.
- Session split: train or test.
- Session bot flag and PageView test flag are explicit boolean fields.

## Edge cases

Four deliberate labelled cases are recorded in `data/ground_truth/ground_truth.csv`. Do not use that file as a model feature or training input.
