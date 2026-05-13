%% Thermal First-Cut Sizing — BEPI Template
% Inputs (optional): Q_internal_W, T_hot_K, T_cold_K, alpha, epsilon, A_ext_m2
% Outputs: radiator_area_m2, heater_power_W, T_equilibrium_K

if ~exist('Q_internal_W','var'),  Q_internal_W = 350; end
if ~exist('T_hot_K','var'),       T_hot_K = 313; end        % 40°C max
if ~exist('T_cold_K','var'),      T_cold_K = 263; end       % -10°C min
if ~exist('alpha','var'),         alpha = 0.3; end          % Solar absorptivity
if ~exist('epsilon','var'),       epsilon = 0.85; end       % IR emissivity (white paint)
if ~exist('A_ext_m2','var'),      A_ext_m2 = 3.0; end      % External surface area
if ~exist('solar_flux','var'),    solar_flux = 1361; end
if ~exist('albedo','var'),        albedo = 0.3; end
if ~exist('earth_IR','var'),      earth_IR = 237; end       % W/m2
if ~exist('view_factor','var'),   view_factor = 0.5; end

sigma = 5.670e-8;

% Hot case — need radiator
Q_solar = alpha * solar_flux * A_ext_m2 * 0.25;           % Projected area ~25%
Q_albedo = alpha * albedo * solar_flux * A_ext_m2 * view_factor * 0.25;
Q_earth = epsilon * earth_IR * A_ext_m2 * view_factor;
Q_env_hot = Q_solar + Q_albedo + Q_earth;

Q_total_hot = Q_internal_W + Q_env_hot;
radiator_area_m2 = Q_total_hot / (epsilon * sigma * T_hot_K^4);

% Cold case — need heater
Q_env_cold = Q_earth * 0.5;    % Eclipse, no solar
Q_radiated_cold = epsilon * sigma * T_cold_K^4 * radiator_area_m2;
heater_power_W = max(0, Q_radiated_cold - Q_internal_W*0.3 - Q_env_cold);

% Equilibrium temperature (hot case, no radiator adjustment)
T_equilibrium_K = (Q_total_hot / (epsilon * sigma * A_ext_m2))^0.25;

fprintf('=== Thermal Sizing Results ===\n');
fprintf('Radiator Area:    %.2f m2\n', radiator_area_m2);
fprintf('Heater Power:     %.1f W\n', heater_power_W);
fprintf('T Equilibrium:    %.1f K (%.1f C)\n', T_equilibrium_K, T_equilibrium_K-273.15);
