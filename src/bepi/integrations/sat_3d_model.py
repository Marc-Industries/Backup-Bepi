from dataclasses import dataclass, field
import math
import numpy as np
import plotly.graph_objects as go


@dataclass
class SubsystemBlock:
    name: str = "Subsystem"
    x_m: float = 0.15
    y_m: float = 0.15
    z_m: float = 0.10
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    color: str = "coral"
    shape: str = "box"  # "box" or "cylinder" (x_m=diameter, z_m=height)


@dataclass
class SatelliteGeometry:
    body_x_m: float = 0.6
    body_y_m: float = 0.6
    body_z_m: float = 0.8
    solar_panel_length_m: float = 1.5
    solar_panel_width_m: float = 0.6
    n_panels: int = 2
    has_antenna: bool = True
    antenna_diameter_m: float = 0.5
    antenna_focal_length_m: float = 0.2
    has_thruster: bool = True
    bus_shape: str = "box"
    bus_diameter_m: float = 1.0
    panel_mounting: str = "deployed_wing"
    panel_cant_angle_deg: float = 0.0
    radiator_area_m2: float = 0.0
    radiator_face: str = "+Y"
    custom_blocks: list = field(default_factory=list)


def _box_faces(cx, cy, cz, dx, dy, dz):
    x = [cx - dx, cx + dx, cx + dx, cx - dx, cx - dx, cx + dx, cx + dx, cx - dx]
    y = [cy - dy, cy - dy, cy + dy, cy + dy, cy - dy, cy - dy, cy + dy, cy + dy]
    z = [cz - dz, cz - dz, cz - dz, cz - dz, cz + dz, cz + dz, cz + dz, cz + dz]
    i = [0, 0, 0, 0, 4, 4, 0, 0, 0, 0, 2, 2]
    j = [1, 2, 1, 5, 5, 6, 1, 4, 3, 4, 3, 6]
    k = [2, 3, 5, 4, 6, 7, 4, 5, 7, 7, 7, 7]
    return x, y, z, i, j, k


def _cylinder_mesh(radius, height, n=36):
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    verts = []
    for t_i in range(n):
        verts.append((radius * cos_t[t_i], radius * sin_t[t_i], -height / 2))
    for t_i in range(n):
        verts.append((radius * cos_t[t_i], radius * sin_t[t_i], height / 2))
    bottom_center = len(verts)
    verts.append((0.0, 0.0, -height / 2))
    top_center = len(verts)
    verts.append((0.0, 0.0, height / 2))
    faces_i, faces_j, faces_k = [], [], []
    for t_i in range(n):
        t_next = (t_i + 1) % n
        b0, b1 = t_i, t_next
        t0, t1 = t_i + n, t_next + n
        faces_i += [b0, b0]
        faces_j += [b1, t0]
        faces_k += [t0, t1]
    for t_i in range(n):
        t_next = (t_i + 1) % n
        faces_i.append(bottom_center)
        faces_j.append(t_next)
        faces_k.append(t_i)
    for t_i in range(n):
        t_next = (t_i + 1) % n
        faces_i.append(top_center)
        faces_j.append(t_i + n)
        faces_k.append(t_next + n)
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return xs, ys, zs, faces_i, faces_j, faces_k


def _hexprism_mesh(apothem, height):
    n = 6
    angles = [math.pi / 6 + i * math.pi / 3 for i in range(n)]
    radius = apothem / math.cos(math.pi / n)
    verts = []
    for a in angles:
        verts.append((radius * math.cos(a), radius * math.sin(a), -height / 2))
    for a in angles:
        verts.append((radius * math.cos(a), radius * math.sin(a), height / 2))
    bottom_center = len(verts)
    verts.append((0.0, 0.0, -height / 2))
    top_center = len(verts)
    verts.append((0.0, 0.0, height / 2))
    faces_i, faces_j, faces_k = [], [], []
    for i in range(n):
        i_next = (i + 1) % n
        b0, b1 = i, i_next
        t0, t1 = i + n, i_next + n
        faces_i += [b0, b0]
        faces_j += [b1, t0]
        faces_k += [t0, t1]
    for i in range(n):
        i_next = (i + 1) % n
        faces_i.append(bottom_center)
        faces_j.append(i_next)
        faces_k.append(i)
    for i in range(n):
        i_next = (i + 1) % n
        faces_i.append(top_center)
        faces_j.append(i + n)
        faces_k.append(i_next + n)
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return xs, ys, zs, faces_i, faces_j, faces_k


def _quad(pts, name=""):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    return go.Mesh3d(x=xs, y=ys, z=zs, i=[0, 0], j=[1, 2], k=[2, 3],
                     name=name, showlegend=bool(name))


def _temp_to_rgb(t, tmin=100, tmax=400):
    frac = np.clip((t - tmin) / (tmax - tmin), 0, 1)
    if frac < 0.5:
        r, g, b = 0, frac * 2, 1 - frac * 2
    else:
        r, g, b = (frac - 0.5) * 2, 1 - (frac - 0.5) * 2, 0
    return f"rgb({int(r*255)},{int(g*255)},{int(b*255)})"


def _face_quad(cx, cy, cz, dx, dy, dz, face):
    h = {
        "+X": [(cx+dx, cy-dy, cz-dz), (cx+dx, cy+dy, cz-dz), (cx+dx, cy+dy, cz+dz), (cx+dx, cy-dy, cz+dz)],
        "-X": [(cx-dx, cy-dy, cz-dz), (cx-dx, cy+dy, cz-dz), (cx-dx, cy+dy, cz+dz), (cx-dx, cy-dy, cz+dz)],
        "+Y": [(cx-dx, cy+dy, cz-dz), (cx+dx, cy+dy, cz-dz), (cx+dx, cy+dy, cz+dz), (cx-dx, cy+dy, cz+dz)],
        "-Y": [(cx-dx, cy-dy, cz-dz), (cx+dx, cy-dy, cz-dz), (cx+dx, cy-dy, cz+dz), (cx-dx, cy-dy, cz+dz)],
        "+Z": [(cx-dx, cy-dy, cz+dz), (cx+dx, cy-dy, cz+dz), (cx+dx, cy+dy, cz+dz), (cx-dx, cy+dy, cz+dz)],
        "-Z": [(cx-dx, cy-dy, cz-dz), (cx+dx, cy-dy, cz-dz), (cx+dx, cy+dy, cz-dz), (cx-dx, cy+dy, cz-dz)],
    }
    return h[face]


def _add_bus_mesh(fig, geometry, thermal_colors):
    g = geometry
    if g.bus_shape == "box":
        hx, hy, hz = g.body_x_m / 2, g.body_y_m / 2, g.body_z_m / 2
        if thermal_colors:
            for face_name in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
                pts = _face_quad(0, 0, 0, hx, hy, hz, face_name)
                temp = thermal_colors.get(face_name, 293)
                color = _temp_to_rgb(temp)
                q = _quad(pts, name=f"Body ({face_name})")
                q.update(color=color, opacity=0.9, hovertext=f"{face_name}: {temp:.0f} K")
                fig.add_trace(q)
        else:
            x, y, z, i, j, k = _box_faces(0, 0, 0, hx, hy, hz)
            fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k,
                                    color="goldenrod", opacity=0.85, name="Body", showlegend=True))
    elif g.bus_shape == "cylinder":
        r = g.bus_diameter_m / 2
        h = g.body_z_m
        x, y, z, i, j, k = _cylinder_mesh(r, h)
        fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k,
                                color="goldenrod", opacity=0.85, name="Body", showlegend=True))
    elif g.bus_shape == "hexagonal_prism":
        apothem = g.bus_diameter_m / 2
        h = g.body_z_m
        x, y, z, i, j, k = _hexprism_mesh(apothem, h)
        fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k,
                                color="goldenrod", opacity=0.85, name="Body", showlegend=True))


def _add_panels(fig, geometry, thermal_colors):
    g = geometry
    if g.panel_mounting == "none" or g.n_panels < 1:
        return
    hx = g.body_x_m / 2
    hy = g.body_y_m / 2 if g.bus_shape == "box" else g.bus_diameter_m / 2
    hz = g.body_z_m / 2
    pl = g.solar_panel_length_m
    pw = g.solar_panel_width_m
    cant = math.radians(g.panel_cant_angle_deg)

    def _wing(sign, label):
        yc = sign * (hy + pl / 2)
        dz = math.sin(cant) * pl / 2
        pts = [(-pw / 2, yc - pl / 2, -dz), (pw / 2, yc - pl / 2, -dz),
               (pw / 2, yc + pl / 2, dz), (-pw / 2, yc + pl / 2, dz)]
        color = "dodgerblue"
        if thermal_colors and label in thermal_colors:
            color = _temp_to_rgb(thermal_colors[label])
        q = _quad(pts, name=label)
        q.update(color=color, opacity=0.8)
        fig.add_trace(q)

    def _body_panel(sign, label):
        pts = [(-pw / 2, -pl / 2, sign * hz),
               (pw / 2, -pl / 2, sign * hz),
               (pw / 2, pl / 2, sign * hz),
               (-pw / 2, pl / 2, sign * hz)]
        color = "dodgerblue"
        if thermal_colors and label in thermal_colors:
            color = _temp_to_rgb(thermal_colors[label])
        q = _quad(pts, name=label)
        q.update(color=color, opacity=0.8)
        fig.add_trace(q)

    mounting = g.panel_mounting
    if mounting == "body_mounted":
        _body_panel(1, "+Z panel")
        if g.n_panels >= 2:
            _body_panel(-1, "-Z panel")
    elif mounting == "deployed_+y":
        _wing(1, "+Y panel")
    elif mounting == "deployed_-y":
        _wing(-1, "-Y panel")
    elif mounting == "both":
        _body_panel(1, "+Z panel")
        if g.n_panels >= 2:
            _body_panel(-1, "-Z panel")
        _wing(1, "+Y panel")
        if g.n_panels >= 2:
            _wing(-1, "-Y panel")
    else:  # deployed_both / deployed_wing (default)
        _wing(1, "+Y panel")
        if g.n_panels >= 2:
            _wing(-1, "-Y panel")


def _add_radiator(fig, geometry):
    g = geometry
    if g.radiator_area_m2 <= 0:
        return
    side = math.sqrt(g.radiator_area_m2)
    hs = side / 2
    hx, hy, hz = g.body_x_m / 2, g.body_y_m / 2, g.body_z_m / 2
    offset = 0.005
    face_map = {
        "+X": [(hx + offset, -hs, -hs), (hx + offset, hs, -hs), (hx + offset, hs, hs), (hx + offset, -hs, hs)],
        "-X": [(-hx - offset, -hs, -hs), (-hx - offset, hs, -hs), (-hx - offset, hs, hs), (-hx - offset, -hs, hs)],
        "+Y": [(-hs, hy + offset, -hs), (hs, hy + offset, -hs), (hs, hy + offset, hs), (-hs, hy + offset, hs)],
        "-Y": [(-hs, -hy - offset, -hs), (hs, -hy - offset, -hs), (hs, -hy - offset, hs), (-hs, -hy - offset, hs)],
        "+Z": [(-hs, -hs, hz + offset), (hs, -hs, hz + offset), (hs, hs, hz + offset), (-hs, hs, hz + offset)],
        "-Z": [(-hs, -hs, -hz - offset), (hs, -hs, -hz - offset), (hs, hs, -hz - offset), (-hs, hs, -hz - offset)],
    }
    pts = face_map.get(g.radiator_face, face_map["+Y"])
    q = _quad(pts, name="Radiator")
    q.update(color="white", opacity=0.7)
    fig.add_trace(q)


def _add_antenna_realistic(fig, geometry):
    g = geometry
    r = g.antenna_diameter_m / 2
    fl = g.antenna_focal_length_m
    hz = g.body_z_m / 2

    n_ring = 24
    n_rad = 10
    theta = np.linspace(0, 2 * np.pi, n_ring, endpoint=False)
    rr = np.linspace(0, r, n_rad)
    th, rv = np.meshgrid(theta, rr)
    xa = rv * np.cos(th)
    ya = rv * np.sin(th)
    za = hz + 0.02 + rv**2 / (4 * fl)

    fig.add_trace(go.Surface(
        x=xa, y=ya, z=za,
        colorscale=[[0, "rgb(180,180,180)"], [1, "rgb(220,220,220)"]],
        showscale=False, name="Dish reflector", opacity=0.92,
        hoverinfo="name",
    ))

    feed_z = hz + 0.02 + fl
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[feed_z],
        mode="markers", marker=dict(size=4, color="red"),
        name="Feed horn", showlegend=True,
    ))

    n_struts = 3
    for i in range(n_struts):
        angle = i * 2 * math.pi / n_struts
        rim_x = r * 0.85 * math.cos(angle)
        rim_y = r * 0.85 * math.sin(angle)
        rim_z = hz + 0.02 + (r * 0.85)**2 / (4 * fl)
        fig.add_trace(go.Scatter3d(
            x=[rim_x, 0], y=[rim_y, 0], z=[rim_z, feed_z],
            mode="lines", line=dict(color="gray", width=3),
            showlegend=False, hoverinfo="skip",
        ))


def _add_subsystem_blocks(fig, geometry):
    for blk in geometry.custom_blocks:
        if not isinstance(blk, SubsystemBlock):
            continue
        if blk.shape == "cylinder":
            r = blk.x_m / 2
            h = blk.z_m
            x, y, z, i, j, k = _cylinder_mesh(r, h, n=24)
            x = [v + blk.offset_x for v in x]
            y = [v + blk.offset_y for v in y]
            z = [v + blk.offset_z for v in z]
        else:
            hx, hy, hz = blk.x_m / 2, blk.y_m / 2, blk.z_m / 2
            x, y, z, i, j, k = _box_faces(blk.offset_x, blk.offset_y, blk.offset_z, hx, hy, hz)
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z, i=i, j=j, k=k,
            color=blk.color, opacity=0.75, name=blk.name, showlegend=True,
        ))


def _add_thermal_nodes_markers(fig, geometry, thermal_temps):
    if not thermal_temps:
        return
    g = geometry
    hx, hy, hz = g.body_x_m / 2, g.body_y_m / 2, g.body_z_m / 2

    node_positions = {
        "+X": (hx + 0.04, 0, 0), "-X": (-hx - 0.04, 0, 0),
        "+Y": (0, hy + 0.04, 0), "-Y": (0, -hy - 0.04, 0),
        "+Z": (0, 0, hz + 0.04), "-Z": (0, 0, -hz - 0.04),
    }

    xs, ys, zs, texts, colors = [], [], [], [], []
    t_vals = list(thermal_temps.values())
    tmin = min(t_vals) if t_vals else 200
    tmax = max(t_vals) if t_vals else 350

    for name, temp in thermal_temps.items():
        pos = node_positions.get(name)
        if pos is None:
            for key in node_positions:
                if key in name:
                    pos = node_positions[key]
                    break
        if pos is None:
            continue
        xs.append(pos[0])
        ys.append(pos[1])
        zs.append(pos[2])
        texts.append(f"{name}<br>{temp:.1f} K ({temp - 273.15:.1f} °C)")
        colors.append(temp)

    if xs:
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs, mode="markers+text",
            marker=dict(
                size=10, color=colors, colorscale="RdBu_r",
                cmin=tmin, cmax=tmax,
                colorbar=dict(title=dict(text="T (K)", font=dict(color="white")),
                              len=0.5, x=1.02, tickfont=dict(color="white")),
                line=dict(width=1, color="white"),
            ),
            text=[f"{t:.0f} K" for t in colors],
            textfont=dict(size=9, color="white"),
            textposition="top center",
            hovertext=texts, hoverinfo="text",
            name="Thermal nodes", showlegend=True,
        ))


_LEGEND_STYLE = dict(
    font=dict(color="white", size=11),
    bgcolor="rgba(10,10,30,0.85)",
    bordercolor="rgba(100,100,150,0.5)",
    borderwidth=1,
)


def plot_satellite_3d(geometry: SatelliteGeometry, thermal_colors: dict | None = None,
                      thermal_temps: dict | None = None,
                      sun_direction: tuple | None = None) -> go.Figure:
    g = geometry
    fig = go.Figure()

    _add_bus_mesh(fig, g, thermal_colors)
    _add_panels(fig, g, thermal_colors)
    _add_radiator(fig, g)

    hx, hy, hz = g.body_x_m / 2, g.body_y_m / 2, g.body_z_m / 2

    if g.has_antenna:
        _add_antenna_realistic(fig, g)

    if g.has_thruster:
        n = 12
        theta = np.linspace(0, 2 * np.pi, n)
        r_nozzle = 0.06
        length = 0.15
        x0 = -hx
        xs = [x0] + [x0 - length] * n
        ys = [0] + (r_nozzle * np.cos(theta)).tolist()
        zs = [0] + (r_nozzle * np.sin(theta)).tolist()
        ii = [0] * n
        jj = list(range(1, n + 1))
        kk = [j % n + 1 for j in range(1, n + 1)]
        fig.add_trace(go.Mesh3d(x=xs, y=ys, z=zs, i=ii, j=jj, k=kk,
                                color="slategray", opacity=0.9, name="Thruster", showlegend=True))

    _add_subsystem_blocks(fig, g)

    if thermal_temps:
        _add_thermal_nodes_markers(fig, g, thermal_temps)

    if sun_direction is not None:
        sd = np.array(sun_direction, dtype=float)
        sd = sd / (np.linalg.norm(sd) + 1e-12)
        scale = max(g.body_x_m, g.body_y_m, g.body_z_m) * 1.5
        tip = sd * scale
        fig.add_trace(go.Scatter3d(x=[0, tip[0]], y=[0, tip[1]], z=[0, tip[2]],
                                   mode="lines+text", line=dict(color="yellow", width=6),
                                   text=["", "Sun ☀"], textposition="top center",
                                   textfont=dict(color="yellow"),
                                   name="Sun direction", showlegend=True))
        fig.add_trace(go.Cone(x=[tip[0]], y=[tip[1]], z=[tip[2]],
                              u=[sd[0]], v=[sd[1]], w=[sd[2]],
                              sizemode="absolute", sizeref=0.08,
                              colorscale=[[0, "yellow"], [1, "yellow"]], showscale=False))

    span = max(hx, hy + g.solar_panel_length_m, hz) * 1.5
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-span, span], showgrid=False, zeroline=False, showticklabels=False, title=""),
            yaxis=dict(range=[-span, span], showgrid=False, zeroline=False, showticklabels=False, title=""),
            zaxis=dict(range=[-span, span], showgrid=False, zeroline=False, showticklabels=False, title=""),
            bgcolor="black",
            aspectmode="data",
        ),
        paper_bgcolor="black",
        font_color="white",
        legend=_LEGEND_STYLE,
        margin=dict(l=0, r=0, t=30, b=0),
        title="3D Satellite Model",
    )
    return fig


def plot_satellite_with_orbit(geometry: SatelliteGeometry, altitude_km: float = 500,
                              inclination_deg: float = 28.5) -> go.Figure:
    R_E = 6371
    r_orbit = R_E + altitude_km

    phi = np.linspace(0, 2 * np.pi, 60)
    theta = np.linspace(0, np.pi, 30)
    ph, th = np.meshgrid(phi, theta)
    xe = R_E * np.sin(th) * np.cos(ph)
    ye = R_E * np.sin(th) * np.sin(ph)
    ze = R_E * np.cos(th)

    fig = go.Figure()
    fig.add_trace(go.Surface(x=xe, y=ye, z=ze,
                             colorscale=[[0, "darkblue"], [0.5, "dodgerblue"], [1, "lightblue"]],
                             showscale=False, opacity=0.7, name="Earth"))

    inc = np.radians(inclination_deg)
    nu = np.linspace(0, 2 * np.pi, 200)
    xo = r_orbit * np.cos(nu)
    yo = r_orbit * np.sin(nu) * np.cos(inc)
    zo = r_orbit * np.sin(nu) * np.sin(inc)
    fig.add_trace(go.Scatter3d(x=xo, y=yo, z=zo, mode="lines",
                               line=dict(color="lime", width=2), name="Orbit"))

    sat_nu = 0.0
    sx = r_orbit * np.cos(sat_nu)
    sy = r_orbit * np.sin(sat_nu) * np.cos(inc)
    sz = r_orbit * np.sin(sat_nu) * np.sin(inc)
    fig.add_trace(go.Scatter3d(x=[sx], y=[sy], z=[sz], mode="markers+text",
                               marker=dict(size=6, color="gold"),
                               text=["Satellite"], textposition="top center",
                               textfont=dict(color="white"),
                               name="Satellite"))

    sun_dir = np.array([1.0, 0.3, 0.1])
    sun_dir = sun_dir / np.linalg.norm(sun_dir)
    arrow_len = r_orbit * 0.6
    tip = sun_dir * arrow_len
    fig.add_trace(go.Scatter3d(x=[0, tip[0]], y=[0, tip[1]], z=[0, tip[2]],
                               mode="lines+text", line=dict(color="yellow", width=4),
                               text=["", "Sun"], textposition="top center",
                               textfont=dict(color="yellow"),
                               name="Sun direction"))

    lim = r_orbit * 1.3
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-lim, lim], showgrid=False, zeroline=False, showticklabels=False, title=""),
            yaxis=dict(range=[-lim, lim], showgrid=False, zeroline=False, showticklabels=False, title=""),
            zaxis=dict(range=[-lim, lim], showgrid=False, zeroline=False, showticklabels=False, title=""),
            bgcolor="black",
            aspectmode="data",
        ),
        paper_bgcolor="black",
        font_color="white",
        legend=_LEGEND_STYLE,
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"Orbit: {altitude_km:.0f} km, inc {inclination_deg:.1f}°",
    )
    return fig


def create_face_to_node_mapping(geometry: SatelliteGeometry) -> dict[str, str]:
    g = geometry
    mapping: dict[str, str] = {}

    if g.bus_shape == "box":
        for face in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
            mapping[face] = f"Body ({face})"
    elif g.bus_shape == "cylinder":
        mapping["lateral"] = "Body (lateral)"
        mapping["+Z"] = "Body (+Z)"
        mapping["-Z"] = "Body (-Z)"
    elif g.bus_shape == "hexagonal_prism":
        for i in range(6):
            mapping[f"hex_face_{i}"] = f"Body (hex face {i})"
        mapping["+Z"] = "Body (+Z)"
        mapping["-Z"] = "Body (-Z)"

    if g.panel_mounting == "body_mounted":
        if g.n_panels >= 1:
            mapping["+Z panel"] = "Solar Panel +Z"
        if g.n_panels >= 2:
            mapping["-Z panel"] = "Solar Panel -Z"
    else:
        if g.n_panels >= 1:
            mapping["+Y panel"] = "Solar Panel +Y"
        if g.n_panels >= 2:
            mapping["-Y panel"] = "Solar Panel -Y"

    if g.has_antenna:
        mapping["antenna"] = "Antenna"
    if g.has_thruster:
        mapping["thruster"] = "Thruster"
    if g.radiator_area_m2 > 0:
        mapping["radiator"] = f"Radiator ({g.radiator_face})"
    return mapping


def geometry_to_sat_faces(geom: SatelliteGeometry) -> list[dict]:
    faces: list[dict] = []
    g = geom

    bus_alpha, bus_eps = 0.3, 0.8
    panel_alpha, panel_eps = 0.92, 0.85
    radiator_alpha, radiator_eps = 0.15, 0.90

    normal_map_6 = {
        "+X": [1.0, 0.0, 0.0], "-X": [-1.0, 0.0, 0.0],
        "+Y": [0.0, 1.0, 0.0], "-Y": [0.0, -1.0, 0.0],
        "+Z": [0.0, 0.0, 1.0], "-Z": [0.0, 0.0, -1.0],
    }

    if g.bus_shape == "box":
        area_map = {
            "+X": g.body_y_m * g.body_z_m, "-X": g.body_y_m * g.body_z_m,
            "+Y": g.body_x_m * g.body_z_m, "-Y": g.body_x_m * g.body_z_m,
            "+Z": g.body_x_m * g.body_y_m, "-Z": g.body_x_m * g.body_y_m,
        }
        for fname in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
            faces.append({"name": fname, "area_m2": area_map[fname],
                          "normal": normal_map_6[fname], "alpha_s": bus_alpha, "epsilon_ir": bus_eps})
    elif g.bus_shape == "cylinder":
        r = g.bus_diameter_m / 2
        lateral_area = 2 * math.pi * r * g.body_z_m
        cap_area = math.pi * r ** 2
        for i in range(4):
            angle = i * math.pi / 2
            n = [math.cos(angle), math.sin(angle), 0.0]
            faces.append({"name": f"cyl_{['+X','+Y','-X','-Y'][i]}", "area_m2": lateral_area / 4,
                          "normal": n, "alpha_s": bus_alpha, "epsilon_ir": bus_eps})
        faces.append({"name": "+Z", "area_m2": cap_area, "normal": [0.0, 0.0, 1.0],
                      "alpha_s": bus_alpha, "epsilon_ir": bus_eps})
        faces.append({"name": "-Z", "area_m2": cap_area, "normal": [0.0, 0.0, -1.0],
                      "alpha_s": bus_alpha, "epsilon_ir": bus_eps})
    elif g.bus_shape == "hexagonal_prism":
        apothem = g.bus_diameter_m / 2
        side_len = 2 * apothem * math.tan(math.pi / 6)
        side_area = side_len * g.body_z_m
        hex_cap = 3 * math.sqrt(3) / 2 * (apothem / math.cos(math.pi / 6)) ** 2
        for i in range(6):
            angle = math.pi / 6 + i * math.pi / 3
            n = [math.cos(angle), math.sin(angle), 0.0]
            faces.append({"name": f"hex_{i}", "area_m2": side_area,
                          "normal": n, "alpha_s": bus_alpha, "epsilon_ir": bus_eps})
        faces.append({"name": "+Z", "area_m2": hex_cap, "normal": [0.0, 0.0, 1.0],
                      "alpha_s": bus_alpha, "epsilon_ir": bus_eps})
        faces.append({"name": "-Z", "area_m2": hex_cap, "normal": [0.0, 0.0, -1.0],
                      "alpha_s": bus_alpha, "epsilon_ir": bus_eps})

    panel_area = g.solar_panel_length_m * g.solar_panel_width_m
    if g.panel_mounting == "body_mounted":
        if g.n_panels >= 1:
            faces.append({"name": "panel_+Z", "area_m2": panel_area,
                          "normal": [0.0, 0.0, 1.0], "alpha_s": panel_alpha, "epsilon_ir": panel_eps})
        if g.n_panels >= 2:
            faces.append({"name": "panel_-Z", "area_m2": panel_area,
                          "normal": [0.0, 0.0, -1.0], "alpha_s": panel_alpha, "epsilon_ir": panel_eps})
    else:
        cant = math.radians(g.panel_cant_angle_deg)
        nz = math.cos(cant)
        ny_abs = math.sin(cant)
        if g.n_panels >= 1:
            faces.append({"name": "panel_+Y", "area_m2": panel_area,
                          "normal": [0.0, ny_abs, nz], "alpha_s": panel_alpha, "epsilon_ir": panel_eps})
        if g.n_panels >= 2:
            faces.append({"name": "panel_-Y", "area_m2": panel_area,
                          "normal": [0.0, -ny_abs, nz], "alpha_s": panel_alpha, "epsilon_ir": panel_eps})

    if g.radiator_area_m2 > 0:
        rad_normal = normal_map_6.get(g.radiator_face, [0.0, 1.0, 0.0])
        faces.append({"name": f"radiator_{g.radiator_face}", "area_m2": g.radiator_area_m2,
                      "normal": rad_normal, "alpha_s": radiator_alpha, "epsilon_ir": radiator_eps})

    return faces


def export_systema_geometry(geometry: SatelliteGeometry) -> str:
    g = geometry
    lines = ["! Systema Geometry Export", "! Generated by BEPI sat_3d_model", ""]
    node_id = 1
    face_map = create_face_to_node_mapping(g)

    default_optical = {"alpha_s": 0.3, "epsilon_ir": 0.8}
    panel_optical = {"alpha_s": 0.92, "epsilon_ir": 0.85}
    radiator_optical = {"alpha_s": 0.15, "epsilon_ir": 0.90}

    hx, hy, hz = g.body_x_m / 2, g.body_y_m / 2, g.body_z_m / 2

    for face_key, node_name in face_map.items():
        opt = default_optical
        if "panel" in face_key.lower() or "Panel" in node_name:
            opt = panel_optical
        elif "radiator" in face_key.lower() or "Radiator" in node_name:
            opt = radiator_optical

        if g.bus_shape == "box" and face_key in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
            area_map = {
                "+X": g.body_y_m * g.body_z_m, "-X": g.body_y_m * g.body_z_m,
                "+Y": g.body_x_m * g.body_z_m, "-Y": g.body_x_m * g.body_z_m,
                "+Z": g.body_x_m * g.body_y_m, "-Z": g.body_x_m * g.body_y_m,
            }
            area = area_map[face_key]
            normal_map = {
                "+X": (1, 0, 0), "-X": (-1, 0, 0),
                "+Y": (0, 1, 0), "-Y": (0, -1, 0),
                "+Z": (0, 0, 1), "-Z": (0, 0, -1),
            }
            nx, ny, nz = normal_map[face_key]
            cx, cy, cz = nx * hx, ny * hy, nz * hz
        elif g.bus_shape == "cylinder" and face_key == "lateral":
            r = g.bus_diameter_m / 2
            area = 2 * math.pi * r * g.body_z_m
            cx, cy, cz = r, 0, 0
            nx, ny, nz = 1, 0, 0
        elif g.bus_shape == "cylinder" and face_key in ["+Z", "-Z"]:
            r = g.bus_diameter_m / 2
            area = math.pi * r ** 2
            sign = 1 if face_key == "+Z" else -1
            cx, cy, cz = 0, 0, sign * g.body_z_m / 2
            nx, ny, nz = 0, 0, sign
        elif "hex_face" in face_key:
            apothem = g.bus_diameter_m / 2
            side_len = 2 * apothem * math.tan(math.pi / 6)
            area = side_len * g.body_z_m
            idx = int(face_key.split("_")[-1])
            angle = math.pi / 6 + idx * math.pi / 3
            nx, ny, nz = math.cos(angle), math.sin(angle), 0
            cx, cy, cz = apothem * nx, apothem * ny, 0
        elif "panel" in face_key.lower():
            area = g.solar_panel_length_m * g.solar_panel_width_m
            cx, cy, cz = 0, 0, 0
            nx, ny, nz = 0, 0, 1
        elif "radiator" in face_key.lower():
            area = g.radiator_area_m2
            normal_map = {
                "+X": (1, 0, 0), "-X": (-1, 0, 0),
                "+Y": (0, 1, 0), "-Y": (0, -1, 0),
                "+Z": (0, 0, 1), "-Z": (0, 0, -1),
            }
            nx, ny, nz = normal_map.get(g.radiator_face, (0, 1, 0))
            cx, cy, cz = nx * hx, ny * hy, nz * hz
        else:
            area = 0.01
            cx, cy, cz = 0, 0, 0
            nx, ny, nz = 0, 0, 1

        lines.append(f"NODE {node_id}  \"{node_name}\"")
        lines.append(f"  CENTER  {cx:.4f}  {cy:.4f}  {cz:.4f}")
        lines.append(f"  NORMAL  {nx:.4f}  {ny:.4f}  {nz:.4f}")
        lines.append(f"  AREA    {area:.6f}")
        lines.append(f"  ALPHA_S {opt['alpha_s']:.3f}")
        lines.append(f"  EPS_IR  {opt['epsilon_ir']:.3f}")
        lines.append("")
        node_id += 1

    return "\n".join(lines)


def export_systema_thermal_input(geometry: SatelliteGeometry,
                                 thermal_nodes: list[dict],
                                 couplings: list[dict],
                                 env_fluxes: dict | None = None) -> str:
    lines = ["! Systema Thermal Input", "! Generated by BEPI sat_3d_model", ""]

    lines.append("! --- GEOMETRY ---")
    lines.append(export_systema_geometry(geometry))
    lines.append("")

    lines.append("! --- THERMAL NODES ---")
    for nd in thermal_nodes:
        nid = nd.get("id", 0)
        name = nd.get("name", "")
        capacity = nd.get("capacity_J_K", 0.0)
        temp_init = nd.get("T_init_K", 293.0)
        ntype = nd.get("type", "diffusion")
        lines.append(f"TNODE {nid}  \"{name}\"  TYPE={ntype}  C={capacity:.2f}  T_INIT={temp_init:.2f}")
    lines.append("")

    lines.append("! --- CONDUCTIVE COUPLINGS (GL) ---")
    for c in couplings:
        n1 = c.get("node1", 0)
        n2 = c.get("node2", 0)
        gl = c.get("GL_W_K", 0.0)
        gr = c.get("GR_m2", 0.0)
        if gl > 0:
            lines.append(f"GL  {n1}  {n2}  {gl:.6f}")
        if gr > 0:
            lines.append(f"GR  {n1}  {n2}  {gr:.6e}")
    lines.append("")

    lines.append("! --- ENVIRONMENT FLUXES ---")
    if env_fluxes:
        lines.append(f"SOLAR_FLUX      {env_fluxes.get('solar_W_m2', 1361.0):.1f}")
        lines.append(f"ALBEDO          {env_fluxes.get('albedo', 0.3):.3f}")
        lines.append(f"EARTH_IR        {env_fluxes.get('earth_IR_W_m2', 237.0):.1f}")
        lines.append(f"DEEP_SPACE_T    {env_fluxes.get('deep_space_T_K', 2.7):.1f}")
    else:
        lines.append("SOLAR_FLUX      1361.0")
        lines.append("ALBEDO          0.300")
        lines.append("EARTH_IR        237.0")
        lines.append("DEEP_SPACE_T    2.7")
    lines.append("")

    return "\n".join(lines)
