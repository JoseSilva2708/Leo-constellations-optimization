import numpy as np
import networkx as nx
from sgp4.api import Satrec, WGS72
from sgp4.exporter import export_tle

GROUND_PAIRS = [
    ("Lisbon-Rome",      (38.7223,  -9.1393),  (41.9028,  12.4964)),
    ("Berlin-Moscow",    (52.5200,  13.4050),  (55.7558,  37.6173)),
    ("Chicago-Miami",   (41.8781,  -87.6298),  (25.7617, -80.1918)),
    ("London-Rome",     (51.5074,  -0.1278),  (41.9028,  12.4964)),
    ("Tokyo-Shanghai",  (35.6895, 139.6917),  (31.2304, 121.4737)),
]



c = 299792.458
R = 6378.137



class Constellation:
    
    def __init__(self, S, P, F, inc, h, angle):
        self.S = S
        self.P = P
        self.F = F
        self.N = P * S
        self.inc = inc
        self.h = h
        self.angle = angle


    # ==========================================================
    #  COST
    # ==========================================================
    def get_cost(self):
        """
        Function that computes the deployment cost of the constellation.

        The cost combines a per-satellite term, 0.4 * (S * P), with a
        per-orbital-plane term, 30 * P.

        :param self: Self

        :returns: Total deployment cost of the constellation.
        """
        total_cost = 0.4 * self.S * self.P + 30 *self.P
        
        return total_cost
    
    
    # ==========================================================
    #  LATENCY
    # ==========================================================
    def get_latency(self, ts, satellites, ground_pairs=GROUND_PAIRS, min_elev=25, duration_s=5400, time_step_s=225, min_isl_alt_km=80.0, penalize_unreachable=True):
        """
        Function that computes the mean and standard deviation of the
        round-trip propagation latency of the constellation.

        For each time instant over the evaluation window, the shortest ground-to-ground
        path is computed for every ground pair. The one-way latency is converted to
        round-trip time (RTT). If a ground pair is unreachable and
        penalize_unreachable=True, a penalty latency of 1e9 ms is returned.

        :param self: Self
        :param ts: Skyfield timescale object used to generate the evaluation times.
        :param satellites: List of satellite objects used to compute the constellation geometry.
        :param ground_pairs: List of ground-station pairs to evaluate, in the format
                            (name, gateway_coordinates, user_terminal_coordinates).
        :param min_elev: Minimum elevation angle in degrees for a satellite to be visible.
        :param duration_s: Total evaluation duration in seconds.
        :param time_step_s: Time step in seconds between evaluation instants.
        :param min_isl_alt_km: Minimum altitude in km required for an inter-satellite link.
        :param penalize_unreachable: If True, returns a penalty latency when no valid
                                    path is available.

        :returns: Tuple with:
            - Mean round-trip latency in milliseconds;
            - Standard deviation of the round-trip latency in milliseconds.
        """
        times = self.__get_times_over_duration__(ts, duration_s, time_step_s)
        sat_lats, sat_lons, sat_xyz = self.__get_sat_geometry__(satellites, times)

        time_latencies = []
        pair_series = {name: [] for name, _, _ in ground_pairs}

        for ti in range(len(times)):
            sat_xyz_t = sat_xyz[:, ti, :]
            sat_lats_t = sat_lats[:, ti]
            sat_lons_t = sat_lons[:, ti]

            pair_latencies_ti = []

            for name, (gw_lat, gw_lon), (ut_lat, ut_lon) in ground_pairs:
                one_way_ms = self.__shortest_ground_to_ground_path_ms__(
                    sat_xyz_t,
                    sat_lats_t,
                    sat_lons_t,
                    gw_lat,
                    gw_lon,
                    ut_lat,
                    ut_lon,
                    min_elev=min_elev,
                    min_isl_alt_km=min_isl_alt_km
                )

                if one_way_ms is None:
                    if penalize_unreachable:
                        return 1e9, 1e9
                    continue

                rtt_ms = 2.0 * one_way_ms
                pair_series[name].append(rtt_ms)
                pair_latencies_ti.append(rtt_ms)

            if len(pair_latencies_ti) == 0:
                if penalize_unreachable:
                    return 1e9, 1e9,
                continue

            time_latencies.append(np.mean(pair_latencies_ti))

        if len(time_latencies) == 0:
            return 1e9, 1e9

        mean_latency = float(np.mean(time_latencies))
        std_latency = float(np.std(time_latencies))

        return mean_latency, std_latency


    
    # ==========================================================
    # COVERAGE
    # ==========================================================
    def get_coverage(self, satellites, times, grid_points, min_elev, K=2):  
        """
        Function that computes the coverage metrics of the constellation.

        Calculates two coverage metrics in a single pass:
        1. K-fold coverage: percentage of grid points covered by at least K satellites.
        2. Mean Best Elevation (MBE): mean elevation of the best visible satellite
        for each visible grid point.

        Coverage is determined geometrically using the maximum central angle:
        theta_max = arccos((R / (R + h)) * cos(min_elev)) - min_elev.

        :param self: Self
        :param satellites: List of Skyfield satellite objects.
        :param times: List of Skyfield time objects over which coverage is evaluated.
        :param grid_points: List of (latitude, longitude) tuples defining the evaluation grid.
        :param min_elev: Minimum elevation angle in degrees for a satellite to be visible.
        :param K: Minimum number of visible satellites required for K-fold coverage.

        :returns: Tuple with:
            - K-fold coverage percentage;
            - Mean Best Elevation in degrees.
        """
        obs_lats = np.radians(np.array([lat for lat, lon in grid_points]))
        obs_lons = np.radians(np.array([lon for lat, lon in grid_points]))
        sin_obs  = np.sin(obs_lats)
        cos_obs  = np.cos(obs_lats)

        subpoints = [sat.at(times).subpoint() for sat in satellites]
        sat_lats  = np.radians(np.array([sp.latitude.degrees  for sp in subpoints]))
        sat_lons  = np.radians(np.array([sp.longitude.degrees for sp in subpoints]))

        # cos_gamma => shape (N_sats, N_times, N_points)
        cos_gamma = (
            np.sin(sat_lats)[:, :, None] * sin_obs[None, None, :] +
            np.cos(sat_lats)[:, :, None] * cos_obs[None, None, :] *
            np.cos(obs_lons[None, None, :] - sat_lons[:, :, None])
        )
        gamma = np.arccos(np.clip(cos_gamma, -1, 1))

        theta_max = np.arccos((R / (R + self.h)) * np.cos(np.radians(min_elev))) - np.radians(min_elev)
        visible_mask = gamma <= theta_max
        count = np.sum(visible_mask, axis=0)
        kfold_pct = np.mean(count >= K) * 100.0

        rho = np.arcsin((R / (R + self.h)) * np.sin(gamma))
        elev = np.degrees(np.pi / 2 - gamma - rho)
        best_elev = np.max(elev, axis=0)
        visible  = best_elev >= min_elev
        mbe_deg  = np.mean(best_elev[visible]) if visible.any() else 0.0

        return kfold_pct, mbe_deg

    
    #=========================================================
    # AUXILIAR FUNCTIONS (Private functions)
    #========================================================= 
    def __generate_tle_for_sat__(self, sat_num, inc, raan, ecc, argp, mean_anom, mean_mot):
        """
        Auxiliary function that generates a two-line TLE for a satellite.

        Creates an SGP4 satellite record from the given orbital elements, exports
        it as a TLE, and replaces the first line's epoch and checksum with fixed
        values.

        :param self: Self
        :param sat_num: Satellite number used in the TLE.
        :param inc: Orbital inclination in degrees.
        :param raan: Right ascension of the ascending node in degrees.
        :param ecc: Orbital eccentricity.
        :param argp: Argument of perigee in degrees.
        :param mean_anom: Mean anomaly in degrees.
        :param mean_mot: Mean motion in revolutions per day.

        :returns: Tuple with the first and second lines of the generated TLE.
        """
        
        from sgp4.api import jday
        jd, fr = jday(2000, 1, 1, 0, 0, 0)

        sat = Satrec()
        sat.sgp4init(
            WGS72,
            'i',
            sat_num,
            (jd + fr) - 2433281.5,
            0.0,
            0.0,
            0.0,
            ecc,
            np.radians(argp),
            np.radians(inc),
            np.radians(mean_anom),
            mean_mot * 60 / 13750.9870831397,
            np.radians(raan)
        )

        line1, line2 = export_tle(sat)

        
        line1 = line1[:7] + "U 00000ABC 00001.00000000 " + line1[33:]
        line1 = line1[:68] + str(sum(int(c) if c.isdigit() else 1 if c == '-' else 0 for c in line1[:68]) % 10)

        return line1, line2


    def __alt_km_to_mean_motion__(self, alt_km):
        """
        Auxiliary function that converts an orbital altitude to mean motion.

        Computes the semi-major axis as Earth's radius plus the orbital altitude,
        then applies Kepler's third law to obtain the mean motion.

        :param self: Self
        :param alt_km: Orbital altitude in kilometers.

        :returns: Mean motion in revolutions per day.
        """
        mu = 398600.4418
        R  = 6378.137
        a  = R + alt_km
        n_rad_s = np.sqrt(mu / a**3)
        return n_rad_s * 86400 / (2 * np.pi)

    def __visible_sats__(self, sat_lats_t, sat_lons_t, obs_lat, obs_lon, min_elev):
        """
        Auxiliary function that identifies the satellites visible from a ground point.

        Uses the same geometric footprint criterion as get_coverage, based on the
        maximum central angle theta_max. For each visible satellite, computes its
        elevation angle and slant range.

        :param self: Self
        :param sat_lats_t: Array with the latitudes of all satellites at the current time, in radians.
        :param sat_lons_t: Array with the longitudes of all satellites at the current time, in radians.
        :param obs_lat: Latitude of the ground observation point in degrees.
        :param obs_lon: Longitude of the ground observation point in degrees.
        :param min_elev: Minimum elevation angle in degrees for a satellite to be visible.

        :returns: Tuple with:
            - Indices of the visible satellites;
            - Elevation angles of all satellites in degrees;
            - Slant ranges of all satellites in kilometers.
        """
        r_sat     = R + self.h
        obs_lat_r = np.radians(obs_lat)
        obs_lon_r = np.radians(obs_lon)

        cos_g = (
            np.sin(sat_lats_t) * np.sin(obs_lat_r) +
            np.cos(sat_lats_t) * np.cos(obs_lat_r) *
            np.cos(obs_lon_r - sat_lons_t)
        )
        gamma = np.arccos(np.clip(cos_g, -1, 1))

        # mesmo critério de footprint que em get_coverage
        theta_max = (
            np.arccos((R / (R + self.h)) * np.cos(np.radians(min_elev)))
            - np.radians(min_elev)
        )
        visible_mask = gamma <= theta_max

        # agora calcula elevação apenas para os visíveis
        rho  = np.arcsin((R / r_sat) * np.sin(gamma))
        elev = np.degrees(np.pi / 2 - gamma - rho)

        # Distância slant via lei dos cossenos
        dist = np.sqrt(R**2 + r_sat**2 - 2 * R * r_sat * np.cos(gamma))

        vis = np.where(visible_mask)[0]
        return vis, elev, dist


    def __get_sat_geometry__(self, satellites, times):
        """
        Auxiliary function that computes the geographic subpoints and spherical
        Cartesian positions of all satellites over the evaluation times.

        Uses Skyfield/SGP4 to obtain each satellite's subpoint, then converts the
        latitude, longitude, and orbital radius into XYZ coordinates.

        :param self: Self
        :param satellites: List of Skyfield satellite objects.
        :param times: Skyfield time objects over which the satellite geometry is evaluated.

        :returns: Tuple with:
            - Satellite latitudes in radians, with shape (N_sats, N_times);
            - Satellite longitudes in radians, with shape (N_sats, N_times);
            - Satellite XYZ positions in kilometers, with shape (N_sats, N_times, 3).
        """
        subpoints = [sat.at(times).subpoint() for sat in satellites]
        sat_lats  = np.radians(np.array([sp.latitude.degrees  for sp in subpoints]))
        sat_lons  = np.radians(np.array([sp.longitude.degrees for sp in subpoints]))

        r_sat   = R + self.h
        sat_xyz = np.stack([
            r_sat * np.cos(sat_lats) * np.cos(sat_lons),
            r_sat * np.cos(sat_lats) * np.sin(sat_lons),
            r_sat * np.sin(sat_lats)
        ], axis=-1)

        return sat_lats, sat_lons, sat_xyz

    def __get_times_over_duration__(self, ts, duration_s, time_step_s):
        """
        Auxiliary function that generates the time instants used to evaluate the
        constellation over a given duration.

        Creates a sequence of UTC times starting at 2000-01-01 00:00:00 and spaced
        by the specified time step.

        :param self: Self
        :param ts: Skyfield timescale object.
        :param duration_s: Total evaluation duration in seconds.
        :param time_step_s: Time step in seconds between consecutive instants.

        :returns: Skyfield time object containing the evaluation instants.
        """
        secs = np.arange(0, duration_s, time_step_s, dtype=float)
        hours = (secs // 3600).astype(int)
        minutes = ((secs % 3600) // 60).astype(int)
        seconds = (secs % 60).astype(float)
        return ts.utc(2000, 1, 1, hours, minutes, seconds)


    def __max_isl_length_km__(self, min_isl_alt_km=80.0):
        """
        Auxiliary function that computes the maximum inter-satellite link (ISL)
        length for the constellation.

        The maximum distance corresponds to the chord between two satellites at
        the constellation altitude whose line of sight is tangent to a sphere at
        the minimum ISL altitude.

        :param self: Self
        :param min_isl_alt_km: Minimum altitude in km that an ISL must maintain
                            above Earth's surface.

        :returns: Maximum ISL length in kilometers.
        """
        return 2.0 * np.sqrt((R + self.h) ** 2 - (R + min_isl_alt_km) ** 2)

    def __isl_clear_of_earth__(self, p1, p2, min_isl_alt_km=80.0):
        """
        Auxiliary function that checks whether an inter-satellite link between two
        satellites remains clear of Earth.

        Computes the point on the link segment closest to Earth's center and verifies
        whether its distance from the center is at least Earth's radius plus the
        minimum ISL altitude.

        :param self: Self
        :param p1: Cartesian position of the first satellite in kilometers.
        :param p2: Cartesian position of the second satellite in kilometers.
        :param min_isl_alt_km: Minimum altitude in km that the link must maintain
                            above Earth's surface.

        :returns: True if the link does not violate the minimum altitude constraint,
                otherwise False.
        """
        d = p2 - p1
        denom = np.dot(d, d)
        if denom == 0:
            return False
        t = -np.dot(p1, d) / denom
        t = np.clip(t, 0.0, 1.0)
        closest = p1 + t * d
        return np.linalg.norm(closest) >= (R + min_isl_alt_km)

    def __create_isl_graph__(self, sat_xyz_t, min_isl_alt_km=80.0):
        """
        Auxiliary function that checks whether an inter-satellite link between two
        satellites remains clear of Earth.

        Computes the point on the link segment closest to Earth's center and verifies
        whether its distance from the center is at least Earth's radius plus the
        minimum ISL altitude.

        :param self: Self
        :param p1: Cartesian position of the first satellite in kilometers.
        :param p2: Cartesian position of the second satellite in kilometers.
        :param min_isl_alt_km: Minimum altitude in km that the link must maintain
                            above Earth's surface.

        :returns: True if the link does not violate the minimum altitude constraint,
                otherwise False.
        """
        
        G = nx.Graph()
        N = self.S * self.P
        G.add_nodes_from(range(N))

        max_isl_km = self.__max_isl_length_km__(min_isl_alt_km)

        for plane in range(self.P):
            for s in range(self.S):
                i = plane * self.S + s

                j_intra = plane * self.S + (s + 1) % self.S
                d_intra = np.linalg.norm(sat_xyz_t[i] - sat_xyz_t[j_intra])
                if d_intra <= max_isl_km and self.__isl_clear_of_earth__(sat_xyz_t[i], sat_xyz_t[j_intra], min_isl_alt_km):
                    G.add_edge(i, j_intra, weight=d_intra / c * 1000.0)

                j_inter = ((plane + 1) % self.P) * self.S + (s + 1) % self.S
                d_inter = np.linalg.norm(sat_xyz_t[i] - sat_xyz_t[j_inter])
                if d_inter <= max_isl_km and self.__isl_clear_of_earth__(sat_xyz_t[i], sat_xyz_t[j_inter], min_isl_alt_km):
                    G.add_edge(i, j_inter, weight=d_inter / c * 1000.0)

        return G


    def __shortest_ground_to_ground_path_ms__(self,sat_xyz_t,sat_lats_t,sat_lons_t,gw_lat,gw_lon,ut_lat,ut_lon,min_elev=25,min_isl_alt_km=80.0):
        """
        Auxiliary function that computes the shortest one-way propagation delay
        between a gateway and a user terminal through the constellation.

        Builds the ISL graph for the current time instant, identifies the satellites
        visible from both ground stations, and connects each station to its visible
        satellites. Edge weights represent propagation delays in milliseconds. The
        shortest path is then computed using Dijkstra's algorithm.

        :param self: Self
        :param sat_xyz_t: Cartesian positions of all satellites at the current time, in kilometers.
        :param sat_lats_t: Latitudes of all satellites at the current time, in radians.
        :param sat_lons_t: Longitudes of all satellites at the current time, in radians.
        :param gw_lat: Latitude of the gateway in degrees.
        :param gw_lon: Longitude of the gateway in degrees.
        :param ut_lat: Latitude of the user terminal in degrees.
        :param ut_lon: Longitude of the user terminal in degrees.
        :param min_elev: Minimum elevation angle in degrees for a satellite to be visible.
        :param min_isl_alt_km: Minimum altitude in km that an ISL must maintain above Earth's surface.

        :returns: Shortest one-way propagation delay in milliseconds, or None if
                either ground station has no visible satellite or no valid path exists.
        """
        
        G = self.__create_isl_graph__(sat_xyz_t, min_isl_alt_km=min_isl_alt_km)

        gw_vis, _, gw_dist = self.__visible_sats__(sat_lats_t, sat_lons_t, gw_lat, gw_lon, min_elev)
        ut_vis, _, ut_dist = self.__visible_sats__(sat_lats_t, sat_lons_t, ut_lat, ut_lon, min_elev)

        if len(gw_vis) == 0 or len(ut_vis) == 0:
            return None

        G.add_node("gw")
        G.add_node("ut")

        for s in gw_vis:
            G.add_edge("gw", int(s), weight=float(gw_dist[s] / c * 1000.0))

        for s in ut_vis:
            G.add_edge(int(s), "ut", weight=float(ut_dist[s] / c * 1000.0))

        try:
            return float(nx.shortest_path_length(G, "gw", "ut", weight="weight"))
        except nx.NetworkXNoPath:
            return None

    
    #=========================================================
    # AUXILIAR FUNCTIONS (Public functions)
    #=========================================================
    def generate_tles(self, S, P, F,angle, inc_deg, alt_km, epoch="26043.12345678", bstar=1.0e-5, ecc=1.0e-7, argp_deg=0.0, name_prefix="sat"):
        """
        Auxiliary function that generates the TLEs for all satellites in a Walker constellation.

        Satellites are distributed across P orbital planes with S satellites per plane.
        The RAAN is uniformly distributed according to the RAAN range, while the phasing
        factor F determines the mean-anomaly offset between planes. The mean motion is
        derived from the orbital altitude.

        :param self: Self
        :param S: Number of satellites per orbital plane.
        :param P: Number of orbital planes.
        :param F: Walker phasing factor.
        :param angle: RAAN range in degrees, usually 180 or 360.
        :param inc_deg: Orbital inclination in degrees.
        :param alt_km: Orbital altitude in kilometers.
        :param epoch: TLE epoch string.
        :param bstar: Drag term used in the TLE.
        :param ecc: Orbital eccentricity.
        :param argp_deg: Argument of perigee in degrees.
        :param name_prefix: Prefix used for the satellite names.

        :returns: List of tuples, where each tuple contains the first and second lines
                of a satellite TLE.
        """
        N = S * P

        tle_pairs = []
        for i in range(N):
            sat_num = 55000 + i
            plane = i // S        
            sat_in_plane = i % S

            raan = (angle / P) * plane
            phase = (360.0 * F / N) * plane
            mean_anom = (360.0 / S * sat_in_plane + phase) % 360.0
            mean_mot = self.__alt_km_to_mean_motion__(alt_km)

            l1, l2 = self.__generate_tle_for_sat__(
                sat_num,
                inc_deg, raan, ecc, argp_deg, mean_anom, mean_mot
            )
            tle_pairs.append((l1, l2))

        return tle_pairs
    
