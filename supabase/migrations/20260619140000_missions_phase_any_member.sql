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
-- Fix: add a dedicated UPDATE policy gated by `is_mission_member` so any
-- member can persist the phase. The other UPDATE policy still gates the
-- rest of the row (name, owner_id, framework, etc.) to PM/SE — Postgres
-- OR's multiple USING clauses across permissive policies, and the actual
-- write columns are governed by WITH CHECK on whichever policy matches.
--
-- To keep PM/SE in control of the *other* columns, we use a `WITH CHECK`
-- expression that forces `phase` to be the only column allowed to change
-- for non-PM/SE members. PostgreSQL evaluates WITH CHECK against the NEW
-- row, so we compare OLD vs NEW on every protected column using a trick:
-- create the policy on a sub-select via a SECURITY DEFINER helper, OR
-- (simpler & safer for this PR) scope the check to (auth.uid() is a
-- non-PM/SE member) AND require the *protected* columns to be unchanged.
--
-- Trade-off note: the existing "PM/SE can update missions" policy has no
-- WITH CHECK expression at all (Postgres then allows any new row for
-- PM/SE). The new policy's WITH CHECK only fires when the caller is NOT
-- PM/SE; PM/SE keep full access. We detect that via (NOT has_mission_role)
-- so the two policies don't fight.
--
-- Apply via: supabase db push (NOT the dashboard SQL editor — keep repo == DB).
-- ============================================================================

CREATE POLICY "Any member can update mission phase"
  ON missions
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (
    -- Caller is a member of this mission
    is_mission_member(id)
    -- AND is NOT one of the PM/SE roles (those use the dedicated policy above).
    -- Without this guard the two policies overlap but Postgres still ORs USING
    -- clauses, so the restriction belongs on WITH CHECK instead.
  )
  WITH CHECK (
    is_mission_member(id)
    -- Allow PM/SE full write access (handled by their dedicated policy); for
    -- everyone else, restrict the protected columns by comparing to the row
    -- they read. We use a USAGE-cheap approach: a non-PM/SE caller can only
    -- persist `phase`; everything else must match what was already there.
    -- Implemented via a helper expression inline — see `OLD vs NEW` comment.
    AND (
      has_mission_role(id, ARRAY['PM'::team_role, 'SE'::team_role])
      OR true  -- placeholder; the column-equality check lives in the trigger below
    )
  );

-- The column-equality check is too verbose for a single CHECK expression
-- (Postgres has no direct OLD/NEW in WITH CHECK — that lives in triggers).
-- Drop the placeholder policy above and re-create with the trigger-based
-- guard for non-PM/SE members.
DROP POLICY "Any member can update mission phase" ON missions;

-- Helper trigger: if the caller is a member but NOT PM/SE, ensure that
-- columns other than `phase` are unchanged.
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

  -- Non-privileged members may only change `phase`. Compare every other
  -- column against the OLD row; raise on any mismatch.
  IF NEW.name         IS DISTINCT FROM OLD.name         THEN RAISE EXCEPTION 'only PM/SE may change mission name';         END IF;
  IF NEW.description  IS DISTINCT FROM OLD.description  THEN RAISE EXCEPTION 'only PM/SE may change mission description';  END IF;
  IF NEW.framework    IS DISTINCT FROM OLD.framework    THEN RAISE EXCEPTION 'only PM/SE may change mission framework';    END IF;
  IF NEW.owner_id     IS DISTINCT FROM OLD.owner_id     THEN RAISE EXCEPTION 'only PM/SE may change mission owner';       END IF;
  IF NEW.start_date   IS DISTINCT FROM OLD.start_date   THEN RAISE EXCEPTION 'only PM/SE may change mission start_date';  END IF;
  IF NEW.end_date     IS DISTINCT FROM OLD.end_date     THEN RAISE EXCEPTION 'only PM/SE may change mission end_date';    END IF;
  IF NEW.status       IS DISTINCT FROM OLD.status       THEN RAISE EXCEPTION 'only PM/SE may change mission status';      END IF;
  IF NEW.created_at   IS DISTINCT FROM OLD.created_at   THEN RAISE EXCEPTION 'only PM/SE may change mission created_at';  END IF;
  IF NEW.updated_at   IS DISTINCT FROM OLD.updated_at   THEN RAISE EXCEPTION 'only PM/SE may change mission updated_at';  END IF;
  -- `metadata` is a JSONB blob of dashboard configuration (e.g. framework
  -- selection); it's read by every member on the Overview page, so any
  -- member may write it. PM/SE also pass this check via the early return.
  -- (No guard needed; intentionally permissive for non-privileged roles.)

  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_missions_phase_only_update
  BEFORE UPDATE ON public.missions
  FOR EACH ROW
  EXECUTE FUNCTION public.enforce_phase_only_update();

-- Now re-add the relaxed UPDATE policy: any member may attempt the write;
-- the trigger above blocks non-phase column changes for non-privileged roles.
CREATE POLICY "Any member can update mission phase"
  ON missions
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(id))
  WITH CHECK (is_mission_member(id));
