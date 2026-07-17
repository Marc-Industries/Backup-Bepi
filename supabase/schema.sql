-- ============================================================================
-- BEPI — canonical database schema (public)
--
-- GENERATED SNAPSHOT of the live Supabase DB (project kcetgbmtjsjsalyaifsf),
-- 2026-06-10, via catalog introspection (Management API). Do NOT hand-edit:
-- change the DB with a migration in supabase/migrations/, then regenerate.
-- 22 tables, 25 enums, RLS policies, functions and triggers included.
-- NOTE: triggers/policies on the auth schema (e.g. handle_new_user on
-- auth.users) live outside public and are not captured here.
-- ============================================================================

-- ---------- ENUM TYPES ----------
CREATE TYPE budget_type AS ENUM ('mass_kg', 'power_w', 'power_peak_w', 'dissipation_w', 'cost_eur', 'cost_nre_eur', 'data_rate_kbps', 'volume_cm3', 'delta_v_ms', 'custom');
CREATE TYPE component_status AS ENUM ('proposed', 'selected', 'qualified', 'flight');
CREATE TYPE criticality AS ENUM ('cat_1', 'cat_2', 'cat_3', 'cat_4');
CREATE TYPE deliverable_status AS ENUM ('not_started', 'in_progress', 'draft', 'under_review', 'approved');
CREATE TYPE dependency_type AS ENUM ('finish_to_start', 'finish_to_finish', 'start_to_start', 'start_to_finish');
CREATE TYPE ft_gate_type AS ENUM ('and', 'or', 'vote_k_of_n');
CREATE TYPE matlab_engine AS ENUM ('matlab', 'octave');
CREATE TYPE maturity AS ENUM ('estimate', 'measured', 'qualified');
CREATE TYPE milestone_status AS ENUM ('planned', 'achieved', 'missed', 'replanned');
CREATE TYPE phase AS ENUM ('0', 'A', 'B1', 'B2', 'C', 'D', 'E1', 'E2', 'F');
CREATE TYPE priority AS ENUM ('mandatory', 'desirable', 'optional');
CREATE TYPE product_level AS ENUM ('mission', 'satellite', 'subsystem', 'equipment', 'component');
CREATE TYPE requirement_category AS ENUM ('functional', 'performance', 'interface', 'environmental', 'design', 'operational', 'reliability', 'safety', 'product_assurance');
CREATE TYPE requirement_level AS ENUM ('stakeholder', 'mission', 'system', 'subsystem', 'equipment');
CREATE TYPE requirement_status AS ENUM ('draft', 'under_review', 'approved', 'deleted');
CREATE TYPE review_status AS ENUM ('not_ready', 'in_preparation', 'ready', 'passed', 'conditional', 'failed');
CREATE TYPE review_type AS ENUM ('MDR', 'PRR', 'SRR', 'PDR', 'CDR', 'QR', 'AR', 'ORR', 'FRR', 'LRR', 'CRR', 'ELR', 'MCR');
CREATE TYPE risk_category AS ENUM ('technical', 'schedule', 'cost', 'programmatic', 'external');
CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE risk_status AS ENUM ('open', 'mitigating', 'accepted', 'closed', 'retired');
CREATE TYPE subsystem_type AS ENUM ('STR', 'TCS', 'EPS', 'AOCS', 'PROP', 'COM', 'CDH', 'MECH', 'PL', 'HRN', 'SW');
CREATE TYPE task_status AS ENUM ('not_started', 'in_progress', 'completed', 'blocked', 'on_hold');
CREATE TYPE team_role AS ENUM ('PM', 'SE', 'SSL', 'QA', 'AIT', 'CM', 'ADMIN');
CREATE TYPE verification_method AS ENUM ('test', 'analysis', 'inspection', 'review', 'demonstration');
CREATE TYPE verification_status AS ENUM ('not_started', 'in_progress', 'passed', 'failed', 'waived');

-- ---------- TABLES ----------
CREATE TABLE budget_limits (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  budget_type budget_type NOT NULL,
  operating_mode_id uuid,
  limit_value double precision NOT NULL,
  unit text NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE budgets (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  node_id uuid NOT NULL,
  budget_type budget_type NOT NULL,
  nominal_value double precision NOT NULL,
  unit text NOT NULL,
  margin_pct double precision DEFAULT 0 NOT NULL,
  maturity maturity DEFAULT 'estimate'::maturity NOT NULL,
  source text,
  notes text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  operating_mode_id uuid,
  quantity integer DEFAULT 1
);

CREATE TABLE documents (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  doc_number text NOT NULL,
  title text NOT NULL,
  doc_type text NOT NULL,
  revision text NOT NULL,
  status deliverable_status DEFAULT 'not_started'::deliverable_status NOT NULL,
  author text,
  file_path text,
  metadata jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE email_queue (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  recipient_email text NOT NULL,
  recipient_name text,
  subject text,
  body text,
  status text DEFAULT 'pending'::text,
  created_at timestamp with time zone DEFAULT now(),
  sent_at timestamp with time zone,
  invitation_id uuid,
  mission_name text,
  invite_code text,
  error_message text,
  retry_count integer DEFAULT 0 NOT NULL
);

CREATE TABLE fault_tree_nodes (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  parent_id uuid,
  node_id uuid,
  gate_type ft_gate_type,
  name text NOT NULL,
  description text,
  probability double precision,
  k_of_n integer,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE fmeca_entries (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  node_id uuid NOT NULL,
  risk_id uuid,
  failure_mode text NOT NULL,
  failure_cause text,
  local_effect text NOT NULL,
  system_effect text NOT NULL,
  severity integer NOT NULL,
  occurrence integer NOT NULL,
  detection integer NOT NULL,
  mitigation text,
  criticality criticality,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE invitations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  role text DEFAULT 'SE'::text,
  subsystem text,
  code text NOT NULL,
  invite_email text NOT NULL,
  invite_name text,
  created_at timestamp with time zone DEFAULT now(),
  used_at timestamp with time zone,
  used_by text,
  status text DEFAULT 'pending'::text,
  email_sent boolean DEFAULT false
);

CREATE TABLE matlab_scripts (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  name text NOT NULL,
  script_path text NOT NULL,
  engine matlab_engine DEFAULT 'octave'::matlab_engine NOT NULL,
  description text,
  input_mapping jsonb,
  output_mapping jsonb,
  last_run timestamp with time zone,
  last_result jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE milestones (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  review_id uuid,
  name text NOT NULL,
  target_date date NOT NULL,
  actual_date date,
  status milestone_status DEFAULT 'planned'::milestone_status NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE mission_members (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role team_role NOT NULL,
  subsystem subsystem_type,
  is_active boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE missions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  description text,
  phase phase,
  orbit_type text,
  target_launch_date date,
  customer text,
  prime_contractor text,
  ecss_tailoring jsonb,
  metadata jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  mass_limit_kg double precision DEFAULT 350 NOT NULL,
  power_limit_w double precision DEFAULT 500 NOT NULL,
  propellant_mass_kg double precision DEFAULT 25 NOT NULL,
  lifetime_years integer DEFAULT 5 NOT NULL
);

CREATE TABLE operating_modes (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  name text NOT NULL,
  description text,
  is_default boolean DEFAULT false NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE product_tree_nodes (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  parent_id uuid,
  level product_level NOT NULL,
  code text NOT NULL,
  name text NOT NULL,
  subsystem_type subsystem_type,
  description text,
  is_leaf boolean DEFAULT false NOT NULL,
  quantity integer DEFAULT 1 NOT NULL,
  manufacturer text,
  part_number text,
  trl integer,
  heritage text,
  status component_status DEFAULT 'proposed'::component_status NOT NULL,
  notes text,
  metadata jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE profiles (
  id uuid NOT NULL,
  full_name text DEFAULT ''::text NOT NULL,
  email text DEFAULT ''::text NOT NULL,
  avatar_url text,
  org text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE requirement_nodes (
  requirement_id uuid NOT NULL,
  node_id uuid NOT NULL
);

CREATE TABLE requirements (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  parent_id uuid,
  req_id text NOT NULL,
  level requirement_level NOT NULL,
  category requirement_category NOT NULL,
  title text NOT NULL,
  text text NOT NULL,
  rationale text,
  priority priority DEFAULT 'mandatory'::priority NOT NULL,
  status requirement_status DEFAULT 'draft'::requirement_status NOT NULL,
  ecss_ref text,
  source text,
  verification_method verification_method,
  verification_status verification_status DEFAULT 'not_started'::verification_status NOT NULL,
  verification_evidence text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE review_deliverables (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  review_id uuid NOT NULL,
  drd_code text,
  title text NOT NULL,
  status deliverable_status DEFAULT 'not_started'::deliverable_status NOT NULL,
  owner text,
  due_date date,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE reviews (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  review_type review_type NOT NULL,
  phase_before phase NOT NULL,
  phase_after phase NOT NULL,
  planned_date date,
  actual_date date,
  status review_status DEFAULT 'not_ready'::review_status NOT NULL,
  board_members jsonb,
  minutes text,
  entry_criteria jsonb,
  action_items jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE risks (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  risk_id text NOT NULL,
  title text NOT NULL,
  description text NOT NULL,
  category risk_category NOT NULL,
  likelihood integer NOT NULL,
  consequence integer NOT NULL,
  risk_level risk_level NOT NULL,
  status risk_status DEFAULT 'open'::risk_status NOT NULL,
  owner text,
  mitigation_strategy text,
  mitigation_actions jsonb,
  residual_likelihood integer,
  residual_consequence integer,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE schedule_tasks (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  name text NOT NULL,
  start_date date,
  end_date date,
  duration_days integer,
  progress_pct double precision DEFAULT 0 NOT NULL,
  assigned_to text,
  status task_status DEFAULT 'not_started'::task_status NOT NULL,
  is_milestone boolean DEFAULT false NOT NULL,
  notes text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  wbs_node_id uuid
);

CREATE TABLE task_dependencies (
  predecessor_id uuid NOT NULL,
  successor_id uuid NOT NULL,
  dependency_type dependency_type DEFAULT 'finish_to_start'::dependency_type NOT NULL,
  lag_days integer DEFAULT 0 NOT NULL
);

CREATE TABLE wbs_nodes (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  mission_id uuid NOT NULL,
  parent_id uuid,
  node_id uuid,
  wbs_code text NOT NULL,
  name text NOT NULL,
  level integer NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- ---------- CONSTRAINTS (PK / UNIQUE / FK / CHECK) ----------
ALTER TABLE budget_limits ADD CONSTRAINT budget_limits_pkey PRIMARY KEY (id);
ALTER TABLE budget_limits ADD CONSTRAINT budget_limits_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE budget_limits ADD CONSTRAINT budget_limits_operating_mode_id_fkey FOREIGN KEY (operating_mode_id) REFERENCES operating_modes(id) ON DELETE SET NULL;
ALTER TABLE budgets ADD CONSTRAINT budgets_pkey PRIMARY KEY (id);
CREATE UNIQUE INDEX budgets_node_type_without_mode_uniq ON public.budgets (node_id, budget_type) WHERE operating_mode_id IS NULL;
CREATE UNIQUE INDEX budgets_node_type_with_mode_uniq ON public.budgets (node_id, budget_type, operating_mode_id) WHERE operating_mode_id IS NOT NULL;
ALTER TABLE budgets ADD CONSTRAINT budgets_node_id_fkey FOREIGN KEY (node_id) REFERENCES product_tree_nodes(id) ON DELETE CASCADE;
ALTER TABLE budgets ADD CONSTRAINT budgets_operating_mode_id_fkey FOREIGN KEY (operating_mode_id) REFERENCES operating_modes(id) ON DELETE SET NULL;
ALTER TABLE documents ADD CONSTRAINT documents_pkey PRIMARY KEY (id);
ALTER TABLE documents ADD CONSTRAINT documents_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE email_queue ADD CONSTRAINT email_queue_pkey PRIMARY KEY (id);
ALTER TABLE email_queue ADD CONSTRAINT email_queue_invitation_id_fkey FOREIGN KEY (invitation_id) REFERENCES invitations(id) ON DELETE CASCADE;
ALTER TABLE fault_tree_nodes ADD CONSTRAINT fault_tree_nodes_pkey PRIMARY KEY (id);
ALTER TABLE fault_tree_nodes ADD CONSTRAINT fault_tree_nodes_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE fault_tree_nodes ADD CONSTRAINT fault_tree_nodes_node_id_fkey FOREIGN KEY (node_id) REFERENCES product_tree_nodes(id) ON DELETE SET NULL;
ALTER TABLE fault_tree_nodes ADD CONSTRAINT fault_tree_nodes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES fault_tree_nodes(id) ON DELETE CASCADE;
ALTER TABLE fmeca_entries ADD CONSTRAINT fmeca_entries_pkey PRIMARY KEY (id);
ALTER TABLE fmeca_entries ADD CONSTRAINT fmeca_entries_node_id_fkey FOREIGN KEY (node_id) REFERENCES product_tree_nodes(id) ON DELETE CASCADE;
ALTER TABLE fmeca_entries ADD CONSTRAINT fmeca_entries_risk_id_fkey FOREIGN KEY (risk_id) REFERENCES risks(id) ON DELETE SET NULL;
ALTER TABLE fmeca_entries ADD CONSTRAINT fmeca_entries_detection_check CHECK (((detection >= 1) AND (detection <= 5)));
ALTER TABLE fmeca_entries ADD CONSTRAINT fmeca_entries_occurrence_check CHECK (((occurrence >= 1) AND (occurrence <= 5)));
ALTER TABLE fmeca_entries ADD CONSTRAINT fmeca_entries_severity_check CHECK (((severity >= 1) AND (severity <= 5)));
ALTER TABLE invitations ADD CONSTRAINT invitations_pkey PRIMARY KEY (id);
ALTER TABLE invitations ADD CONSTRAINT invitations_code_key UNIQUE (code);
ALTER TABLE invitations ADD CONSTRAINT invitations_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE matlab_scripts ADD CONSTRAINT matlab_scripts_pkey PRIMARY KEY (id);
ALTER TABLE matlab_scripts ADD CONSTRAINT matlab_scripts_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE milestones ADD CONSTRAINT milestones_pkey PRIMARY KEY (id);
ALTER TABLE milestones ADD CONSTRAINT milestones_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE milestones ADD CONSTRAINT milestones_review_id_fkey FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE SET NULL;
ALTER TABLE mission_members ADD CONSTRAINT mission_members_pkey PRIMARY KEY (id);
ALTER TABLE mission_members ADD CONSTRAINT mission_members_mission_id_user_id_role_key UNIQUE (mission_id, user_id, role);
ALTER TABLE mission_members ADD CONSTRAINT unique_mission_user UNIQUE (mission_id, user_id);
ALTER TABLE mission_members ADD CONSTRAINT mission_members_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE mission_members ADD CONSTRAINT mission_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE CASCADE;
ALTER TABLE missions ADD CONSTRAINT missions_pkey PRIMARY KEY (id);
ALTER TABLE operating_modes ADD CONSTRAINT operating_modes_pkey PRIMARY KEY (id);
ALTER TABLE operating_modes ADD CONSTRAINT operating_modes_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE product_tree_nodes ADD CONSTRAINT product_tree_nodes_pkey PRIMARY KEY (id);
ALTER TABLE product_tree_nodes ADD CONSTRAINT product_tree_nodes_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE product_tree_nodes ADD CONSTRAINT product_tree_nodes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES product_tree_nodes(id) ON DELETE CASCADE;
ALTER TABLE product_tree_nodes ADD CONSTRAINT product_tree_nodes_trl_check CHECK (((trl >= 1) AND (trl <= 9)));
ALTER TABLE profiles ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);
ALTER TABLE profiles ADD CONSTRAINT profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE requirement_nodes ADD CONSTRAINT requirement_nodes_pkey PRIMARY KEY (requirement_id, node_id);
ALTER TABLE requirement_nodes ADD CONSTRAINT requirement_nodes_node_id_fkey FOREIGN KEY (node_id) REFERENCES product_tree_nodes(id) ON DELETE CASCADE;
ALTER TABLE requirement_nodes ADD CONSTRAINT requirement_nodes_requirement_id_fkey FOREIGN KEY (requirement_id) REFERENCES requirements(id) ON DELETE CASCADE;
ALTER TABLE requirements ADD CONSTRAINT requirements_pkey PRIMARY KEY (id);
ALTER TABLE requirements ADD CONSTRAINT requirements_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE requirements ADD CONSTRAINT requirements_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES requirements(id) ON DELETE SET NULL;
ALTER TABLE review_deliverables ADD CONSTRAINT review_deliverables_pkey PRIMARY KEY (id);
ALTER TABLE review_deliverables ADD CONSTRAINT review_deliverables_review_id_fkey FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE;
ALTER TABLE reviews ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);
ALTER TABLE reviews ADD CONSTRAINT reviews_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE risks ADD CONSTRAINT risks_pkey PRIMARY KEY (id);
ALTER TABLE risks ADD CONSTRAINT risks_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE risks ADD CONSTRAINT risks_consequence_check CHECK (((consequence >= 1) AND (consequence <= 5)));
ALTER TABLE risks ADD CONSTRAINT risks_likelihood_check CHECK (((likelihood >= 1) AND (likelihood <= 5)));
ALTER TABLE risks ADD CONSTRAINT risks_residual_consequence_check CHECK (((residual_consequence >= 1) AND (residual_consequence <= 5)));
ALTER TABLE risks ADD CONSTRAINT risks_residual_likelihood_check CHECK (((residual_likelihood >= 1) AND (residual_likelihood <= 5)));
ALTER TABLE schedule_tasks ADD CONSTRAINT schedule_tasks_pkey PRIMARY KEY (id);
ALTER TABLE schedule_tasks ADD CONSTRAINT schedule_tasks_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE schedule_tasks ADD CONSTRAINT schedule_tasks_wbs_node_id_fkey FOREIGN KEY (wbs_node_id) REFERENCES wbs_nodes(id) ON DELETE SET NULL;
ALTER TABLE task_dependencies ADD CONSTRAINT task_dependencies_pkey PRIMARY KEY (predecessor_id, successor_id);
ALTER TABLE task_dependencies ADD CONSTRAINT task_dependencies_predecessor_id_fkey FOREIGN KEY (predecessor_id) REFERENCES schedule_tasks(id) ON DELETE CASCADE;
ALTER TABLE task_dependencies ADD CONSTRAINT task_dependencies_successor_id_fkey FOREIGN KEY (successor_id) REFERENCES schedule_tasks(id) ON DELETE CASCADE;
ALTER TABLE wbs_nodes ADD CONSTRAINT wbs_nodes_pkey PRIMARY KEY (id);
ALTER TABLE wbs_nodes ADD CONSTRAINT wbs_nodes_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE;
ALTER TABLE wbs_nodes ADD CONSTRAINT wbs_nodes_node_id_fkey FOREIGN KEY (node_id) REFERENCES product_tree_nodes(id) ON DELETE SET NULL;
ALTER TABLE wbs_nodes ADD CONSTRAINT wbs_nodes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES wbs_nodes(id) ON DELETE CASCADE;

-- ---------- INDEXES ----------
CREATE INDEX idx_budget_limits_mission ON public.budget_limits USING btree (mission_id);
CREATE INDEX idx_budgets_node ON public.budgets USING btree (node_id);
CREATE INDEX idx_documents_mission ON public.documents USING btree (mission_id);
CREATE INDEX idx_email_queue_created ON public.email_queue USING btree (created_at);
CREATE INDEX idx_email_queue_status ON public.email_queue USING btree (status);
CREATE INDEX idx_fault_tree_mission ON public.fault_tree_nodes USING btree (mission_id);
CREATE INDEX idx_fmeca_node ON public.fmeca_entries USING btree (node_id);
CREATE INDEX idx_matlab_scripts_mission ON public.matlab_scripts USING btree (mission_id);
CREATE INDEX idx_milestones_mission ON public.milestones USING btree (mission_id);
CREATE INDEX idx_mission_members_lookup ON public.mission_members USING btree (user_id, mission_id) WHERE (is_active = true);
CREATE INDEX idx_mission_members_mission ON public.mission_members USING btree (mission_id);
CREATE INDEX idx_mission_members_user ON public.mission_members USING btree (user_id);
CREATE INDEX idx_operating_modes_mission ON public.operating_modes USING btree (mission_id);
CREATE INDEX idx_product_tree_mission ON public.product_tree_nodes USING btree (mission_id);
CREATE INDEX idx_product_tree_parent ON public.product_tree_nodes USING btree (parent_id);
CREATE INDEX idx_requirements_mission ON public.requirements USING btree (mission_id);
CREATE INDEX idx_review_deliverables_review ON public.review_deliverables USING btree (review_id);
CREATE INDEX idx_reviews_mission ON public.reviews USING btree (mission_id);
CREATE INDEX idx_risks_mission ON public.risks USING btree (mission_id);
CREATE INDEX idx_schedule_tasks_mission ON public.schedule_tasks USING btree (mission_id);
CREATE INDEX idx_wbs_mission ON public.wbs_nodes USING btree (mission_id);

-- ---------- FUNCTIONS ----------
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
  insert into public.profiles (id, full_name, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    coalesce(new.email, '')
  );
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.has_mission_role(p_mission_id uuid, p_roles team_role[])
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  select exists (
    select 1 from mission_members
    where mission_id = p_mission_id
      and user_id = auth.uid()
      and role = any(p_roles)
      and is_active = true
  );
$function$;

CREATE OR REPLACE FUNCTION public.is_mission_member(p_mission_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
  select exists (
    select 1 from mission_members
    where mission_id = p_mission_id
      and user_id = auth.uid()
      and is_active = true
  );
$function$;

CREATE OR REPLACE FUNCTION public.trigger_invitation_email()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
  insert into public.email_queue (
    invitation_id,
    recipient_email,
    recipient_name,
    mission_name,
    invite_code,
    status
  ) values (
    new.id,
    new.invite_email,
    new.invite_name,
    (select name from public.missions where id = new.mission_id limit 1),
    new.code,
    'pending'
  );
  return new;
end;
$function$;

CREATE OR REPLACE FUNCTION public.update_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
begin
  new.updated_at = now();
  return new;
end;
$function$;

-- ---------- TRIGGERS ----------
CREATE TRIGGER trg_budget_limits_updated_at BEFORE UPDATE ON public.budget_limits FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_budgets_updated_at BEFORE UPDATE ON public.budgets FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON public.documents FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_fault_tree_nodes_updated_at BEFORE UPDATE ON public.fault_tree_nodes FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_fmeca_entries_updated_at BEFORE UPDATE ON public.fmeca_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_invitation_email AFTER INSERT ON public.invitations FOR EACH ROW EXECUTE FUNCTION trigger_invitation_email();
CREATE TRIGGER trg_matlab_scripts_updated_at BEFORE UPDATE ON public.matlab_scripts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_milestones_updated_at BEFORE UPDATE ON public.milestones FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_missions_updated_at BEFORE UPDATE ON public.missions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_operating_modes_updated_at BEFORE UPDATE ON public.operating_modes FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_product_tree_nodes_updated_at BEFORE UPDATE ON public.product_tree_nodes FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_requirements_updated_at BEFORE UPDATE ON public.requirements FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_review_deliverables_updated_at BEFORE UPDATE ON public.review_deliverables FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_reviews_updated_at BEFORE UPDATE ON public.reviews FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_risks_updated_at BEFORE UPDATE ON public.risks FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_schedule_tasks_updated_at BEFORE UPDATE ON public.schedule_tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_wbs_nodes_updated_at BEFORE UPDATE ON public.wbs_nodes FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------- ROW LEVEL SECURITY ----------
ALTER TABLE budget_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE fault_tree_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE fmeca_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE matlab_scripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE missions ENABLE ROW LEVEL SECURITY;
ALTER TABLE operating_modes ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_tree_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirement_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE review_deliverables ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE risks ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE wbs_nodes ENABLE ROW LEVEL SECURITY;

-- ---------- POLICIES ----------
CREATE POLICY "Members can insert" ON budget_limits
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON budget_limits
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON budget_limits
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON budget_limits
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert budgets" ON budgets
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = budgets.node_id) AND is_mission_member(ptn.mission_id)))));
CREATE POLICY "Members can update budgets" ON budgets
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = budgets.node_id) AND is_mission_member(ptn.mission_id)))));
CREATE POLICY "Members can view budgets" ON budgets
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = budgets.node_id) AND is_mission_member(ptn.mission_id)))));
CREATE POLICY "PM/SE can delete budgets" ON budgets
  AS PERMISSIVE FOR DELETE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = budgets.node_id) AND has_mission_role(ptn.mission_id, ARRAY['PM'::team_role, 'SE'::team_role])))));
CREATE POLICY "Members can insert" ON documents
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON documents
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON documents
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON documents
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert" ON fault_tree_nodes
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON fault_tree_nodes
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON fault_tree_nodes
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON fault_tree_nodes
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert fmeca" ON fmeca_entries
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = fmeca_entries.node_id) AND is_mission_member(ptn.mission_id)))));
CREATE POLICY "Members can update fmeca" ON fmeca_entries
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = fmeca_entries.node_id) AND is_mission_member(ptn.mission_id)))));
CREATE POLICY "Members can view fmeca" ON fmeca_entries
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = fmeca_entries.node_id) AND is_mission_member(ptn.mission_id)))));
CREATE POLICY "PM/SE can delete fmeca" ON fmeca_entries
  AS PERMISSIVE FOR DELETE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM product_tree_nodes ptn
  WHERE ((ptn.id = fmeca_entries.node_id) AND has_mission_role(ptn.mission_id, ARRAY['PM'::team_role, 'SE'::team_role])))));
CREATE POLICY "admins can insert invitations" ON invitations
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((EXISTS ( SELECT 1
   FROM mission_members mm
  WHERE ((mm.mission_id = invitations.mission_id) AND (mm.user_id = auth.uid()) AND (mm.is_active = true) AND (mm.role = 'ADMIN'::team_role)))));
CREATE POLICY "admins can select invitations" ON invitations
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM mission_members mm
  WHERE ((mm.mission_id = invitations.mission_id) AND (mm.user_id = auth.uid()) AND (mm.is_active = true) AND (mm.role = 'ADMIN'::team_role)))));
CREATE POLICY "Members can insert" ON matlab_scripts
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON matlab_scripts
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON matlab_scripts
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON matlab_scripts
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert" ON milestones
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON milestones
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON milestones
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON milestones
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can view team" ON mission_members
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM can delete members" ON mission_members
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role]));
CREATE POLICY "PM can insert members" ON mission_members
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (has_mission_role(mission_id, ARRAY['PM'::team_role]));
CREATE POLICY "PM can update members" ON mission_members
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role]))
  WITH CHECK (has_mission_role(mission_id, ARRAY['PM'::team_role]));
CREATE POLICY "Authenticated can create missions" ON missions
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((auth.uid() IS NOT NULL));
CREATE POLICY "Members can view their missions" ON missions
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(id));
CREATE POLICY "PM can delete missions" ON missions
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(id, ARRAY['PM'::team_role]));
CREATE POLICY "PM/SE can update missions" ON missions
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (has_mission_role(id, ARRAY['PM'::team_role, 'SE'::team_role]))
  WITH CHECK (has_mission_role(id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert" ON operating_modes
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON operating_modes
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON operating_modes
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON operating_modes
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert" ON product_tree_nodes
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON product_tree_nodes
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON product_tree_nodes
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON product_tree_nodes
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Users can update own profile" ON profiles
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING ((id = auth.uid()))
  WITH CHECK ((id = auth.uid()));
CREATE POLICY "Users can view own profile" ON profiles
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((id = auth.uid()));
CREATE POLICY "Users can view teammates" ON profiles
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM (mission_members mm1
     JOIN mission_members mm2 ON ((mm1.mission_id = mm2.mission_id)))
  WHERE ((mm1.user_id = auth.uid()) AND (mm2.user_id = profiles.id) AND (mm1.is_active = true) AND (mm2.is_active = true)))));
CREATE POLICY "Members can delete req_nodes" ON requirement_nodes
  AS PERMISSIVE FOR DELETE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM requirements r
  WHERE ((r.id = requirement_nodes.requirement_id) AND has_mission_role(r.mission_id, ARRAY['PM'::team_role, 'SE'::team_role])))));
CREATE POLICY "Members can insert req_nodes" ON requirement_nodes
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((EXISTS ( SELECT 1
   FROM requirements r
  WHERE ((r.id = requirement_nodes.requirement_id) AND is_mission_member(r.mission_id)))));
CREATE POLICY "Members can view req_nodes" ON requirement_nodes
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM requirements r
  WHERE ((r.id = requirement_nodes.requirement_id) AND is_mission_member(r.mission_id)))));
CREATE POLICY "Members can insert" ON requirements
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON requirements
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON requirements
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON requirements
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert deliverables" ON review_deliverables
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((EXISTS ( SELECT 1
   FROM reviews r
  WHERE ((r.id = review_deliverables.review_id) AND is_mission_member(r.mission_id)))));
CREATE POLICY "Members can update deliverables" ON review_deliverables
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM reviews r
  WHERE ((r.id = review_deliverables.review_id) AND is_mission_member(r.mission_id)))));
CREATE POLICY "Members can view deliverables" ON review_deliverables
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM reviews r
  WHERE ((r.id = review_deliverables.review_id) AND is_mission_member(r.mission_id)))));
CREATE POLICY "PM/SE can delete deliverables" ON review_deliverables
  AS PERMISSIVE FOR DELETE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM reviews r
  WHERE ((r.id = review_deliverables.review_id) AND has_mission_role(r.mission_id, ARRAY['PM'::team_role, 'SE'::team_role])))));
CREATE POLICY "Members can insert" ON reviews
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON reviews
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON reviews
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON reviews
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert" ON risks
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON risks
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON risks
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON risks
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can insert" ON schedule_tasks
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON schedule_tasks
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON schedule_tasks
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON schedule_tasks
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
CREATE POLICY "Members can delete task_deps" ON task_dependencies
  AS PERMISSIVE FOR DELETE TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM schedule_tasks st
  WHERE ((st.id = task_dependencies.predecessor_id) AND has_mission_role(st.mission_id, ARRAY['PM'::team_role, 'SE'::team_role])))));
CREATE POLICY "Members can insert task_deps" ON task_dependencies
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK ((EXISTS ( SELECT 1
   FROM schedule_tasks st
  WHERE ((st.id = task_dependencies.predecessor_id) AND is_mission_member(st.mission_id)))));
CREATE POLICY "Members can view task_deps" ON task_dependencies
  AS PERMISSIVE FOR SELECT TO authenticated
  USING ((EXISTS ( SELECT 1
   FROM schedule_tasks st
  WHERE ((st.id = task_dependencies.predecessor_id) AND is_mission_member(st.mission_id)))));
CREATE POLICY "Members can insert" ON wbs_nodes
  AS PERMISSIVE FOR INSERT TO authenticated
  WITH CHECK (is_mission_member(mission_id));
CREATE POLICY "Members can update" ON wbs_nodes
  AS PERMISSIVE FOR UPDATE TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "Members can view" ON wbs_nodes
  AS PERMISSIVE FOR SELECT TO authenticated
  USING (is_mission_member(mission_id));
CREATE POLICY "PM/SE can delete" ON wbs_nodes
  AS PERMISSIVE FOR DELETE TO authenticated
  USING (has_mission_role(mission_id, ARRAY['PM'::team_role, 'SE'::team_role]));
