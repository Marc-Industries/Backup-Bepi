-- Ensure each product-tree node has at most one budget row per budget_type
-- (one mass_kg + one power_w). Without this UNIQUE constraint, .upsert() on the
-- budgets table resolves the conflict on the primary key (id) and therefore
-- inserts a brand-new row on every save, accumulating duplicate budget rows.
--
-- The application code (streamlit_app.py) was changed to update-then-insert so
-- it no longer depends on this constraint, but the constraint is the real
-- database-level guarantee against duplicates.
--
-- Safe to apply only when no duplicates already exist. If any exist, dedupe
-- first (keep the most recent row per node_id/budget_type):
--   DELETE FROM public.budgets a
--   USING public.budgets b
--   WHERE a.ctid < b.ctid
--     AND a.node_id = b.node_id
--     AND a.budget_type = b.budget_type;

ALTER TABLE public.budgets
  ADD CONSTRAINT budgets_node_type_uniq UNIQUE (node_id, budget_type);
