# Multi-Plane Mission ROS 2 Workspace

This workspace launches two ArduPlane vehicles in SITL, connects both of them to QGroundControl (QGC), and starts one MAVROS-backed waypoint mission node per plane.

The current setup assumes:

- QGC is already running
- QGC is listening on UDP ports `14550` and `14560`
- ROS 2 and MAVROS are installed
- ArduPilot SITL tools such as `sim_vehicle.py` are installed

## Workspace Layout

- ROS 2 package: `multi_plane_mission`
- Dual-plane launch: `/Users/purandhar/Downloads/ros2_ws-main/src/multi_plane_mission/launch/multi_plane.launch.py`
- Single-plane launch: `/Users/purandhar/Downloads/ros2_ws-main/src/multi_plane_mission/launch/single_plane.launch.py`

## Port Plan

Use this port mapping so QGC and MAVROS can both receive telemetry without conflicting:

| Vehicle | QGC UDP | MAVROS UDP |
| --- | --- | --- |
| Plane 1 | `14550` | `14540` |
| Plane 2 | `14560` | `14541` |

That means each SITL instance sends to two destinations:

- one UDP stream for QGC
- one UDP stream for MAVROS

## 1. Build the ROS 2 Package

Open a terminal and run:

```bash
cd /Users/purandhar/Downloads/ros2_ws-main
source /opt/ros/<your_ros2_distro>/setup.bash
colcon build --packages-select multi_plane_mission
source install/setup.bash
```

Replace `<your_ros2_distro>` with your distro name, for example `humble`.

## 2. Start Plane 1 SITL

Open a new terminal and run:

```bash
sim_vehicle.py -v ArduPlane -I0 --sysid 1 \
  --out=udp:127.0.0.1:14550 \
  --out=udp:127.0.0.1:14540
```

Notes:

- `14550` sends telemetry to QGC for plane 1
- `14540` sends telemetry to MAVROS for plane 1

## 3. Start Plane 2 SITL

Open another terminal and run:

```bash
sim_vehicle.py -v ArduPlane -I1 --sysid 2 \
  --out=udp:127.0.0.1:14560 \
  --out=udp:127.0.0.1:14541
```

Notes:

- `14560` sends telemetry to QGC for plane 2
- `14541` sends telemetry to MAVROS for plane 2

## 4. Launch MAVROS and Both Mission Nodes

Open a third terminal and run:

```bash
cd /Users/purandhar/Downloads/ros2_ws-main
source /opt/ros/<your_ros2_distro>/setup.bash
source install/setup.bash

ros2 launch multi_plane_mission multi_plane.launch.py \
  plane1_fcu_url:=udp://@127.0.0.1:14540 \
  plane2_fcu_url:=udp://@127.0.0.1:14541
```

This launch file starts:

- `plane1/mavros`
- `plane2/mavros`
- `plane1/mission`
- `plane2/mission`

Do not set `gcs_url` in this workflow, because QGC is already receiving MAVLink directly from SITL on `14550` and `14560`.

## 5. Expected Behavior

If everything is connected correctly:

- QGC should show two separate vehicles
- `/plane1/mavros/state` should report a connected FCU
- `/plane2/mavros/state` should report a connected FCU
- each mission node should upload waypoints, set the mission start index, arm, and switch to `AUTO`

## 6. Quick Verification Commands

In a sourced ROS 2 terminal:

```bash
ros2 topic list | grep mavros
ros2 topic echo /plane1/mavros/state
ros2 topic echo /plane2/mavros/state
```

You can also check that the mission nodes are present:

```bash
ros2 node list
```

## 7. Single-Plane Smoke Test

If you want to verify only one vehicle first:

1. Start only plane 1 SITL
2. Launch the single-plane stack

```bash
cd /Users/purandhar/Downloads/ros2_ws-main
source /opt/ros/<your_ros2_distro>/setup.bash
source install/setup.bash

ros2 launch multi_plane_mission single_plane.launch.py \
  fcu_url:=udp://@127.0.0.1:14540
```

## 8. Customizing Missions

The default missions for the two planes are defined directly in the dual-plane launch file. Each mission node gets:

- a MAVROS namespace
- one takeoff point
- a list of waypoint latitudes
- a list of waypoint longitudes
- a list of waypoint altitudes

To change the route, edit:

- `/Users/purandhar/Downloads/ros2_ws-main/src/multi_plane_mission/launch/multi_plane.launch.py`
- `/Users/purandhar/Downloads/ros2_ws-main/src/multi_plane_mission/launch/single_plane.launch.py`

The mission execution logic lives in:

- `/Users/purandhar/Downloads/ros2_ws-main/src/multi_plane_mission/multi_plane_mission/mission_node.py`

## 9. Troubleshooting

### `colcon: command not found`

Install ROS 2 build tools and make sure your ROS environment is sourced before building.

### QGC only sees one vehicle

Check that:

- plane 1 is sending to `14550`
- plane 2 is sending to `14560`
- each SITL instance uses a different `--sysid`

### MAVROS does not connect

Check that:

- plane 1 SITL is sending to `14540`
- plane 2 SITL is sending to `14541`
- the ROS launch command uses the same FCU URLs

### Mission upload succeeds but plane does not fly

ArduPlane can refuse arming or mode transitions if pre-arm conditions are not satisfied. Watch:

- the SITL console output
- QGC messages
- `ros2 topic echo /plane1/mavros/state`
- `ros2 topic echo /plane2/mavros/state`

If needed, add a takeoff helper or adjust ArduPilot parameters for your SITL scenario.

## 10. Typical Terminal Layout

- Terminal 1: Plane 1 SITL
- Terminal 2: Plane 2 SITL
- Terminal 3: ROS 2 launch for MAVROS + mission nodes
- QGC: already running and listening on `14550` and `14560`
