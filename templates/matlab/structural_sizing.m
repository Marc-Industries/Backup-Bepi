%% Structural First-Cut Sizing — BEPI Template
% Inputs (optional): mass_kg, n_axial_g, n_lateral_g, panel_L_m, panel_W_m, material
% Outputs: panel_thickness_mm, structural_mass_kg, first_freq_Hz

if ~exist('mass_kg','var'),       mass_kg = 300; end
if ~exist('n_axial_g','var'),     n_axial_g = 8; end       % Quasi-static axial
if ~exist('n_lateral_g','var'),   n_lateral_g = 4; end     % Quasi-static lateral
if ~exist('panel_L_m','var'),     panel_L_m = 0.8; end
if ~exist('panel_W_m','var'),     panel_W_m = 0.6; end
if ~exist('SF','var'),            SF = 1.25; end           % Safety factor (ECSS)
if ~exist('MoS_min','var'),       MoS_min = 0.0; end

% Al 7075-T6 properties
E_Pa = 71.7e9;         % Young's modulus
rho_kgm3 = 2810;       % Density
sigma_y_Pa = 503e6;    % Yield strength
sigma_u_Pa = 572e6;    % Ultimate strength

g = 9.81;

% Loads
F_axial = mass_kg * n_axial_g * g * SF;
F_lateral = mass_kg * n_lateral_g * g * SF;
F_combined = sqrt(F_axial^2 + F_lateral^2);

% Panel sizing (simplified honeycomb panel)
A_panel = panel_L_m * panel_W_m;
sigma_applied = F_combined / A_panel;

% Required thickness (bending-dominated)
% Simplified: t = 6*M / (sigma_allow * W) for uniformly loaded panel
M_max = F_combined * panel_L_m / 8;    % Simply supported, uniform load approx
sigma_allow = sigma_y_Pa / SF;
t_required = sqrt(6 * M_max / (sigma_allow * panel_W_m));
panel_thickness_mm = t_required * 1000;

% Margin of Safety
MoS = sigma_allow / sigma_applied - 1;

% Structural mass estimate (15-20% of total for smallsat)
structural_mass_kg = mass_kg * 0.18;

% First natural frequency (cantilevered panel, simplified)
I_panel = panel_W_m * t_required^3 / 12;
m_per_length = rho_kgm3 * panel_W_m * t_required;
first_freq_Hz = 3.516 / (2*pi) * sqrt(E_Pa * I_panel / (m_per_length * panel_L_m^4));

fprintf('=== Structural Sizing Results ===\n');
fprintf('Panel Thickness:    %.1f mm\n', panel_thickness_mm);
fprintf('Structural Mass:    %.1f kg\n', structural_mass_kg);
fprintf('Margin of Safety:   %.2f\n', MoS);
fprintf('1st Natural Freq:   %.1f Hz\n', first_freq_Hz);
fprintf('Axial Load:         %.0f N\n', F_axial);
fprintf('Lateral Load:       %.0f N\n', F_lateral);
