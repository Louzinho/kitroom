-- Order history with relational joins, used by the order list screens.
CREATE VIEW v_order_history AS
SELECT o.order_id, o.user_id, u.full_name, u.email, o.total_amount, o.order_status,
       o.shipping_address, o.created_at, o.updated_at,
       COALESCE(SUM(i.quantity), 0) AS item_count
FROM orders o
JOIN users u ON u.user_id = o.user_id
LEFT JOIN order_items i ON i.order_id = o.order_id
GROUP BY o.order_id;
