-- Support one power allocation per equipment node and operating mode.
-- Existing power rows are preserved and associated with an "Operation" mode.

-- Each mission gets a default operational mode when it does not have one yet.
INSERT INTO public.operating_modes (mission_id, name, description, is_default)
SELECT m.id, 'Operation', 'Legacy nominal operating mode', true
FROM public.missions AS m
WHERE NOT EXISTS (
    SELECT 1
    FROM public.operating_modes AS om
    WHERE om.mission_id = m.id
);

-- Repair older data that has modes but no (or multiple) defaults.
WITH ranked_modes AS (
    SELECT id,
           row_number() OVER (
               PARTITION BY mission_id
               ORDER BY is_default DESC, created_at, id
           ) AS position
    FROM public.operating_modes
)
UPDATE public.operating_modes AS om
SET is_default = (ranked_modes.position = 1)
FROM ranked_modes
WHERE om.id = ranked_modes.id;

-- A mission must have at most one default mode and mode names must be unique
-- within the mission (case-insensitively).
CREATE UNIQUE INDEX IF NOT EXISTS operating_modes_one_default_per_mission
    ON public.operating_modes (mission_id)
    WHERE is_default;

CREATE UNIQUE INDEX IF NOT EXISTS operating_modes_name_per_mission
    ON public.operating_modes (mission_id, lower(name));

-- Move legacy power data to the default mode of the corresponding mission.
UPDATE public.budgets AS b
SET operating_mode_id = om.id
FROM public.product_tree_nodes AS n
JOIN public.operating_modes AS om
  ON om.mission_id = n.mission_id
 AND om.is_default
WHERE b.node_id = n.id
  AND b.budget_type = 'power_w'
  AND b.operating_mode_id IS NULL;

ALTER TABLE public.budgets
    DROP CONSTRAINT IF EXISTS budgets_node_type_uniq;

-- Mass remains mode-independent.  Power (and any future mode-aware budget)
-- can have one row per node/mode.
CREATE UNIQUE INDEX IF NOT EXISTS budgets_node_type_without_mode_uniq
    ON public.budgets (node_id, budget_type)
    WHERE operating_mode_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS budgets_node_type_with_mode_uniq
    ON public.budgets (node_id, budget_type, operating_mode_id)
    WHERE operating_mode_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS budget_limits_type_mode_uniq
    ON public.budget_limits (mission_id, budget_type, operating_mode_id)
    WHERE operating_mode_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_budgets_operating_mode
    ON public.budgets (operating_mode_id);
