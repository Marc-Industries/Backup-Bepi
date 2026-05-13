%% Power Budget Sizing — BEPI Template
% Inputs: SA_area_m2, BAT_Wh
% Optional: eta_sa, solar_flux, eclipse_frac, P_nominal_W, P_eclipse_W
% Outputs: power_margin_pct, SA_power_W, DOD_pct, battery_cycles

if ~exist('SA_area_m2','var'),    SA_area_m2 = 2.0; end
if ~exist('BAT_Wh','var'),        BAT_Wh = 120; end
if ~exist('eta_sa','var'),        eta_sa = 0.30; end          % Triple-junction GaAs
if ~exist('solar_flux','var'),    solar_flux = 1361; end      % W/m2 at 1 AU
if ~exist('eclipse_frac','var'),  eclipse_frac = 0.35; end    % LEO ~35%
if ~exist('P_nominal_W','var'),   P_nominal_W = 350; end
if ~exist('P_eclipse_W','var'),   P_eclipse_W = 200; end
if ~exist('orbit_period_min','var'), orbit_period_min = 96; end

% SA power generation (BOL)
SA_power_W = SA_area_m2 * solar_flux * eta_sa;

% Degradation (5 years, 2.5%/year)
degradation = (1 - 0.025)^5;
SA_power_EOL = SA_power_W * degradation;

% Sun time power available after loads
sun_frac = 1 - eclipse_frac;
eclipse_min = orbit_period_min * eclipse_frac;

% Energy balance per orbit
E_generated = SA_power_EOL * orbit_period_min * sun_frac;  % W-min
E_consumed = P_nominal_W * orbit_period_min * sun_frac + P_eclipse_W * eclipse_min;

power_margin_pct = (E_generated / E_consumed - 1) * 100;

% Battery DOD
E_eclipse_Wh = P_eclipse_W * eclipse_min / 60;
DOD_pct = E_eclipse_Wh / BAT_Wh * 100;

% Cycle life estimate (Li-ion, simplified)
if DOD_pct < 20
    battery_cycles = 30000;
elseif DOD_pct < 40
    battery_cycles = 15000;
else
    battery_cycles = 5000;
end

fprintf('=== Power Budget Results ===\n');
fprintf('SA Power BOL:    %.1f W\n', SA_power_W);
fprintf('SA Power EOL:    %.1f W\n', SA_power_EOL);
fprintf('Power Margin:    %.1f %%\n', power_margin_pct);
fprintf('Battery DOD:     %.1f %%\n', DOD_pct);
fprintf('Battery Cycles:  %d\n', battery_cycles);
