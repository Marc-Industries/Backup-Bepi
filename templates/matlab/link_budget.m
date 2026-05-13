%% Link Budget Analysis — BEPI Template
% Inputs (from .mat): P_tx_W, G_tx_dBi, G_rx_dBi
% Optional: freq_Hz, distance_km, data_rate_bps, Ts_K
% Outputs: link_margin (dB), Eb_N0 (dB), EIRP (dBW)

% Defaults if not provided
if ~exist('freq_Hz','var'),      freq_Hz = 8.2e9; end        % X-band
if ~exist('distance_km','var'),  distance_km = 600; end      % LEO
if ~exist('data_rate_bps','var'),data_rate_bps = 2e6; end    % 2 Mbps
if ~exist('Ts_K','var'),         Ts_K = 300; end             % System noise temp
if ~exist('P_tx_W','var'),       P_tx_W = 5; end
if ~exist('G_tx_dBi','var'),     G_tx_dBi = 6; end
if ~exist('G_rx_dBi','var'),     G_rx_dBi = 40; end

% Constants
c = 2.998e8;
k_B = 1.381e-23;

% Calculations
P_tx_dBW = 10*log10(P_tx_W);
EIRP = P_tx_dBW + G_tx_dBi;

lambda_m = c / freq_Hz;
FSPL = 20*log10(4*pi*distance_km*1e3/lambda_m);   % Free space path loss

% Received power
P_rx_dBW = EIRP - FSPL + G_rx_dBi;

% Noise
N0_dBW_Hz = 10*log10(k_B * Ts_K);

% Eb/N0
Eb_N0 = P_rx_dBW - N0_dBW_Hz - 10*log10(data_rate_bps);

% Required Eb/N0 (QPSK, BER=1e-6)
Eb_N0_req = 10.5;

% Link margin
link_margin = Eb_N0 - Eb_N0_req;

fprintf('=== Link Budget Results ===\n');
fprintf('EIRP:         %.1f dBW\n', EIRP);
fprintf('FSPL:         %.1f dB\n', FSPL);
fprintf('Eb/N0:        %.1f dB\n', Eb_N0);
fprintf('Required:     %.1f dB\n', Eb_N0_req);
fprintf('Link Margin:  %.1f dB\n', link_margin);
