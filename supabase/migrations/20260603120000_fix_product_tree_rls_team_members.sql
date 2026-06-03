-- ============================================================================
-- Fix product_tree_nodes RLS policies.
--
-- Root cause:
--   1. The "Product tree write" policy referenced mission_members, but the
--      project uses team_members. Every INSERT/UPDATE/DELETE was therefore
--      silently rejected by RLS — the client received an empty error and
--      `window.location.reload()` on the frontend re-rendered the demo mock
--      tree, making the new node look like it "disappeared".
--   2. The "Allow all" policies that preceded the real ones were dead code
--      (immediately dropped and replaced) but created noise.
--   3. FOR ALL bundled INSERT/UPDATE/DELETE behind one check, which is
--      fine functionally but harder to reason about. Split for clarity.
--
-- Apply via: supabase db push
-- (or paste into the Supabase SQL editor if you don't run migrations locally)
-- ============================================================================

ALTER TABLE public.product_tree_nodes ENABLE ROW LEVEL SECURITY;

-- Drop every policy on this table so we can re-apply cleanly.
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

-- SELECT: any member of the mission can read the tree.
CREATE POLICY "Product tree select"
  ON public.product_tree_nodes
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.mission_id = product_tree_nodes.mission_id
        AND tm.user_id = auth.uid()
    )
  );

-- INSERT: only PM, SE, ADMIN, SSL of that mission.
CREATE POLICY "Product tree insert"
  ON public.product_tree_nodes
  FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.mission_id = product_tree_nodes.mission_id
        AND tm.user_id = auth.uid()
        AND tm.role IN ('PM', 'SE', 'ADMIN', 'SSL')
    )
  );

-- UPDATE: same gate as INSERT.
CREATE POLICY "Product tree update"
  ON public.product_tree_nodes
  FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.mission_id = product_tree_nodes.mission_id
        AND tm.user_id = auth.uid()
        AND tm.role IN ('PM', 'SE', 'ADMIN', 'SSL')
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.mission_id = product_tree_nodes.mission_id
        AND tm.user_id = auth.uid()
        AND tm.role IN ('PM', 'SE', 'ADMIN', 'SSL')
    )
  );

-- DELETE: same gate as INSERT for now.
CREATE POLICY "Product tree delete"
  ON public.product_tree_nodes
  FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.team_members tm
      WHERE tm.mission_id = product_tree_nodes.mission_id
        AND tm.user_id = auth.uid()
        AND tm.role IN ('PM', 'SE', 'ADMIN', 'SSL')
    )
  );
