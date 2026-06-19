-- ============================================================================
-- missions: any mission member may update the `phase` column
--
-- The existing "PM/SE can update missions" policy restricts UPDATE on the
-- `missions` table to PM/SE only. The Budget Dashboard's phase selector
-- therefore fails with
--   permission denied for function has_mission_role
-- for every non-PM/SE member ("USER" / "QA" / "CM" / etc.), even though
-- changing the mission phase is a benign action all members need.
--
-- Fix (3 parts):
--   1. GRANT EXECUTE on the SECURITY DEFINER helpers to the `authenticated`
--      role. Without this, any RLS policy that references has_mission_role()
--      or is_mission_member() evaluated as the calling user raises 42501
--      "permission denied for function" — even when the underlying
--      function would have returned false. The repository's own error
--      handler in src/bepi/onboarding.py documents this exact symptom.
--   2. New permissive UPDATE policy gated by is_mission_member() so any
--      mission member can persist `phase` (and `metadata`). PM/SE keep
--      full access via the existing policy.
--   3. A BEFORE UPDATE trigger that prevents non-privileged members from
--      changing columns other than `phase` / `metadata`. PM/SE bypass
--      via an early return.
--
-- Apply via: supabase db push (NOT the dashboard SQL editor — keep repo == DB).
-- ============================================================================

-- 1) Grants: required for the RLS policies below to compile without 42501.
--    These are idempotent; re-running is safe.
GRANT EXECUTE ON FUNCTION public.is_mission_member(uuid)        TO authenticated;
GRANT EXECUTE ON FUNCTION public.has_mission_role(uuid, team_role[]) TO authenticated;

-- 2) + 3) The trigger-based guard for non-privileged members.

CREATE OR REPLACE FUNCTION public.enforce_phase_only_update()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _is_privileged boolean;
BEGIN
  _is_privileged := public.has_mission_role(
    NEW.id, ARRAY['PM'::team_role, 'SE'::team_role]
  );
  IF _is_privileged THEN
    RETURN NEW;  -- PM/SE keep full access.
  END IF;

  -- Non-privileged members may only change `phase` and `metadata`.
  -- Compare every other column against the OLD row; raise on any mismatch.
  IF NEW.name         IS DISTINCT FROM OLD.name         THEN RAISE EXCEPTION 'only PM/SE may change mission name';         END IF;
  IF NEW.description  IS DISTINCT FROM OLD.description  THEN RAISE EXCEPTION 'only PM/SE may change mission description';  END IF;
  IF NEW.framework    IS DISTINCT FROM OLD.framework    THEN RAISE EXCEPTION 'only PM/SE may change mission framework';    END IF;
  IF NEW.owner_id     IS DISTINCT FROM OLD.owner_id     THEN RAISE EXCEPTION 'only PM/SE may change mission owner';       END IF;
  IF NEW.start_date   IS DISTINCT FROM OLD.start_date   THEN RAISE EXCEPTION 'only PM/SE may change mission start_date';  END IF;
  IF NEW.end_date     IS DISTINCT FROM OLD.end_date     THEN RAISE EXCEPTION 'only PM/SE may change mission end_date';    END IF;
  IF NEW.status       IS DISTINCT FROM OLD.status       THEN RAISE EXCEPTION 'only PM/SE may change mission status';      END IF;
  IF NEW.created_at   IS DISTINCT FROM OLD.created_at   THEN RAISE EXCEPTION 'only PM/SE may change mission created_at';  END IF;
  IF NEW.updated_at   IS DISTINCT FROM OLD.updated_at   THEN RAISE EXCEPTION 'only PM/SE may change mission updated_at';  END IF;
  -- `phase` and `metadata` are intentionally NOT guarded: the Budget
  -- Dashboard's phase selector and the framework picker both write here,
  -- and any member is allowed to set them.

  RETURN NEW;
END;
$$;

-- Idempotent trigger: drop first so re-runs work.
DROP TRIGGER IF EXISTS trg_missions_phase_only_update ON public.missions;
CREATE TRIGGER trg_missions_phase_only_update
  BEFORE UPDATE ON public.missions
  FOR EACH ROW
  EXECUTE FUNCTION public.enforce_phase_only_update();

-- Permissive UPDATE policy: any mission member can attempt the write.
-- The trigger above blocks non-phase column changes for non-privileged
-- roles. PM/SE also satisfy USING via the original "PM/SE can update
-- missions" policy (Postgres ORs USING across permissive policies).
DROP POLICY IF EXISTS "Any member can update mission phase" ON missions;
CREATE POLICY "Any member can update mission phase"
  ON missions
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(id))
  WITH CHECK (is_mission_member(id));
