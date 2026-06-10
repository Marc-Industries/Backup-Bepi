-- ============================================================================
-- product_tree_nodes RLS policies (reconciled 2026-06-10).
--
-- This migration originally referenced a `team_members` table that does NOT
-- exist in this project (the membership table is `mission_members`, accessed
-- through the SECURITY DEFINER helpers is_mission_member()/has_mission_role()).
-- As written it would, on `supabase db push`, DROP every policy and then fail
-- to recreate them ("relation team_members does not exist") — leaving the table
-- with RLS enabled and no policies, i.e. all access denied. The live DB was
-- fixed by hand via the SQL editor with the correct helper-based policies; this
-- file is rewritten to match that live state so the repo is reproducible.
--
-- Apply via: supabase db push (NOT the dashboard SQL editor — keep repo == DB).
-- ============================================================================

ALTER TABLE public.product_tree_nodes ENABLE ROW LEVEL SECURITY;

-- Drop every policy on this table so we can re-apply cleanly (idempotent).
DO $$
DECLARE p record;
BEGIN
  FOR p IN
    SELECT policyname FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'product_tree_nodes'
  LOOP
    EXECUTE format('DROP POLICY %I ON public.product_tree_nodes', p.policyname);
  END LOOP;
END $$;

-- SELECT / INSERT / UPDATE: any active member of the mission.
CREATE POLICY "Members can view"
  ON public.product_tree_nodes FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));

CREATE POLICY "Members can insert"
  ON public.product_tree_nodes FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));

CREATE POLICY "Members can update"
  ON public.product_tree_nodes FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));

-- DELETE: PM/SE only (matches live).
-- NOTE: current members are all ADMIN, so no one can delete the tree through
-- the user client until ADMIN is added here. Left as-is to mirror live; adjust
-- with a follow-up migration (add 'ADMIN'::team_role) if delete is needed.
CREATE POLICY "PM/SE can delete"
  ON public.product_tree_nodes FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
