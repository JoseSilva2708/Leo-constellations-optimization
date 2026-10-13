# The MIT License (MIT)
#
# Copyright (c) 2020 ETH Zurich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

dynamic_state_update_interval_ms = 225000                         # 225s update interval
simulation_end_time_s = 5400                                      # 5400 seconds
pingmesh_interval_ns = 100 * 1000 * 1000                         # A ping every 100ms
enable_isl_utilization_tracking = False                           # Enable utilization tracking
isl_utilization_tracking_interval_ns = 1 * 1000 * 1000 * 1000    # 1 second utilization intervals

# Derivatives
dynamic_state_update_interval_ns = dynamic_state_update_interval_ms * 1000 * 1000
simulation_end_time_ns = simulation_end_time_s * 1000 * 1000 * 1000
dynamic_state = "dynamic_state_" + str(dynamic_state_update_interval_ms) + "ms_for_" + str(simulation_end_time_s) + "s"

# Chosen pairs:
full_satellite_network_isls = "my_walker_test_isls_plus_grid_ground_stations_algorithm_free_one_only_over_isls"


def get_chosen_pairs(num_sats):
    LISBON = num_sats + 0
    ROME = num_sats + 1
    BERLIN = num_sats + 2
    MOSCOW = num_sats + 3
    CHICAGO = num_sats + 4
    MIAMI = num_sats + 5
    LONDON = num_sats + 6
    TOKYO = num_sats + 7
    SHANGHAI = num_sats + 8

    return [
        ("my_constellation_isls", LISBON, ROME, "TcpNewReno", full_satellite_network_isls),
        ("my_constellation_isls", LISBON, ROME, "TcpVegas", full_satellite_network_isls),

        ("my_constellation_isls", BERLIN, MOSCOW, "TcpNewReno", full_satellite_network_isls),
        ("my_constellation_isls", BERLIN, MOSCOW, "TcpVegas", full_satellite_network_isls),

        ("my_constellation_isls", CHICAGO, MIAMI, "TcpNewReno", full_satellite_network_isls),
        ("my_constellation_isls", CHICAGO, MIAMI, "TcpVegas", full_satellite_network_isls),

        ("my_constellation_isls", LONDON, ROME, "TcpNewReno", full_satellite_network_isls),
        ("my_constellation_isls", TOKYO, SHANGHAI, "TcpNewReno", full_satellite_network_isls),
    ]


# def get_tcp_run_list(num_sats):
#     chosen_pairs = get_chosen_pairs(num_sats)
#     run_list = []
#     for p in chosen_pairs:
#         run_list += [
#             {
#                 "name": p[0] + "_" + str(p[1]) + "_to_" + str(p[2]) + "_with_" + p[3] + "_at_10_Mbps",
#                 "satellite_network": p[4],
#                 "dynamic_state": dynamic_state,
#                 "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
#                 "simulation_end_time_ns": simulation_end_time_ns,
#                 "data_rate_megabit_per_s": 10.0,
#                 "queue_size_pkt": 100,
#                 "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
#                 "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
#                 "from_id": p[1],
#                 "to_id": p[2],
#                 "tcp_socket_type": p[3],
#             },
#         ]
#
#     return run_list


def get_pings_run_list(num_sats):
    chosen_pairs = get_chosen_pairs(num_sats)

    reduced_chosen_pairs = []
    for p in chosen_pairs:
        if not (p[0], p[1], p[2], p[4]) in reduced_chosen_pairs:
            reduced_chosen_pairs.append((p[0], p[1], p[2], p[4]))

    run_list = []
    for p in reduced_chosen_pairs:
        run_list += [
            {
                "name": p[0] + "_" + str(p[1]) + "_to_" + str(p[2]) + "_pings",
                "satellite_network": p[3],
                "dynamic_state": dynamic_state,
                "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
                "simulation_end_time_ns": simulation_end_time_ns,
                "data_rate_megabit_per_s": 10000.0,
                "queue_size_pkt": 100000,
                "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
                "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
                "from_id": p[1],
                "to_id": p[2],
                "pingmesh_interval_ns": pingmesh_interval_ns,
            }
        ]

    return run_list


def get_udp_run_list(num_sats):
    chosen_pairs = get_chosen_pairs(num_sats)

    run_list = []

    for p in chosen_pairs:
        run_list += [
            {
                "name": p[0] + "_" + str(p[1]) + "_to_" + str(p[2]) + "_udp_at_10_Mbps",
                "satellite_network": p[4],
                "dynamic_state": dynamic_state,
                "dynamic_state_update_interval_ns": dynamic_state_update_interval_ns,
                "simulation_end_time_ns": simulation_end_time_ns,
                "data_rate_megabit_per_s": 10.0,
                "queue_size_pkt": 100,
                "enable_isl_utilization_tracking": enable_isl_utilization_tracking,
                "isl_utilization_tracking_interval_ns": isl_utilization_tracking_interval_ns,
                "from_id": p[1],
                "to_id": p[2],
            },
        ]

    return run_list
