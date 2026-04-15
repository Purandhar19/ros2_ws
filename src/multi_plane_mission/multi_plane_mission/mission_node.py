import rclpy
from rclpy.node import Node

from mavros_msgs.msg import State, Waypoint
from mavros_msgs.srv import CommandBool, SetMode, WaypointPush, WaypointSetCurrent


def _normalize_ns(namespace: str) -> str:
    namespace = namespace.strip()
    if not namespace.startswith('/'):
        namespace = f'/{namespace}'
    return namespace.rstrip('/')


class PlaneMission(Node):

    def __init__(self):
        super().__init__('plane_mission')

        self.declare_parameter('mavros_ns', '/plane1/mavros')
        self.declare_parameter('guided_mode', 'GUIDED')
        self.declare_parameter('auto_mode', 'AUTO')
        self.declare_parameter('arm_before_auto', True)
        self.declare_parameter('mission_start_index', 0)
        self.declare_parameter('takeoff_lat', 38.3148)
        self.declare_parameter('takeoff_lon', -76.5489)
        self.declare_parameter('takeoff_alt', 60.0)
        self.declare_parameter('waypoint_lats', [38.3150, 38.3155, 38.3160])
        self.declare_parameter('waypoint_lons', [-76.5495, -76.5500, -76.5490])
        self.declare_parameter('waypoint_alts', [60.0, 60.0, 60.0])

        self.mavros_ns = _normalize_ns(
            self.get_parameter('mavros_ns').get_parameter_value().string_value
        )
        self.guided_mode = self.get_parameter('guided_mode').value
        self.auto_mode = self.get_parameter('auto_mode').value
        self.arm_before_auto = self.get_parameter('arm_before_auto').value
        self.mission_start_index = self.get_parameter('mission_start_index').value
        self.takeoff_lat = self.get_parameter('takeoff_lat').value
        self.takeoff_lon = self.get_parameter('takeoff_lon').value
        self.takeoff_alt = self.get_parameter('takeoff_alt').value
        self.waypoint_lats = list(self.get_parameter('waypoint_lats').value)
        self.waypoint_lons = list(self.get_parameter('waypoint_lons').value)
        self.waypoint_alts = list(self.get_parameter('waypoint_alts').value)

        self._validate_waypoint_parameters()

        self.state = State()
        self.create_subscription(
            State,
            f'{self.mavros_ns}/state',
            self.state_cb,
            10,
        )

        self.arming_client = self.create_client(
            CommandBool,
            f'{self.mavros_ns}/cmd/arming',
        )
        self.mode_client = self.create_client(
            SetMode,
            f'{self.mavros_ns}/set_mode',
        )
        self.wp_client = self.create_client(
            WaypointPush,
            f'{self.mavros_ns}/mission/push',
        )
        self.set_current_client = self.create_client(
            WaypointSetCurrent,
            f'{self.mavros_ns}/mission/set_current',
        )

        self.wait_for_services()
        self.run_mission()

    def _validate_waypoint_parameters(self):
        if not self.waypoint_lats:
            raise ValueError('At least one navigation waypoint is required.')
        if len(self.waypoint_lats) != len(self.waypoint_lons):
            raise ValueError('waypoint_lats and waypoint_lons must have the same length.')
        if len(self.waypoint_lats) != len(self.waypoint_alts):
            raise ValueError('waypoint_lats and waypoint_alts must have the same length.')

    def state_cb(self, msg):
        self.state = msg

    def wait_for_services(self):
        clients = [
            ('arming', self.arming_client),
            ('set_mode', self.mode_client),
            ('mission_push', self.wp_client),
            ('mission_set_current', self.set_current_client),
        ]
        for label, client in clients:
            while rclpy.ok() and not client.wait_for_service(timeout_sec=1.0):
                self.get_logger().info(
                    f'[{self.mavros_ns}] waiting for {label} service...'
                )

    def create_mission(self):
        wp_list = []

        def wp(cmd, lat, lon, alt):
            waypoint = Waypoint()
            waypoint.frame = 3
            waypoint.command = int(cmd)
            waypoint.is_current = False
            waypoint.autocontinue = True
            waypoint.x_lat = float(lat)
            waypoint.y_long = float(lon)
            waypoint.z_alt = float(alt)
            return waypoint

        takeoff = wp(22, self.takeoff_lat, self.takeoff_lon, self.takeoff_alt)
        takeoff.is_current = True
        wp_list.append(takeoff)

        for lat, lon, alt in zip(
            self.waypoint_lats,
            self.waypoint_lons,
            self.waypoint_alts,
        ):
            wp_list.append(wp(16, lat, lon, alt))

        return wp_list

    def _call_and_check(self, client, request, description):
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        result = future.result()
        if result is None:
            raise RuntimeError(f'[{self.mavros_ns}] {description} failed: no response')
        if hasattr(result, 'success') and not result.success:
            raise RuntimeError(f'[{self.mavros_ns}] {description} failed')
        if hasattr(result, 'mode_sent') and not result.mode_sent:
            raise RuntimeError(f'[{self.mavros_ns}] {description} was rejected')
        return result

    def run_mission(self):
        while rclpy.ok() and not self.state.connected:
            self.get_logger().info(f'[{self.mavros_ns}] waiting for FCU connection...')
            rclpy.spin_once(self, timeout_sec=1.0)

        self.get_logger().info(f'[{self.mavros_ns}] connected to FCU')

        push_request = WaypointPush.Request()
        push_request.waypoints = self.create_mission()
        self._call_and_check(self.wp_client, push_request, 'mission upload')
        self.get_logger().info(f'[{self.mavros_ns}] mission uploaded')

        set_current_request = WaypointSetCurrent.Request()
        set_current_request.wp_seq = int(self.mission_start_index)
        self._call_and_check(
            self.set_current_client,
            set_current_request,
            'mission reset',
        )
        self.get_logger().info(
            f'[{self.mavros_ns}] mission start waypoint set to '
            f'{self.mission_start_index}'
        )

        guided_request = SetMode.Request()
        guided_request.custom_mode = self.guided_mode
        self._call_and_check(self.mode_client, guided_request, 'guided mode switch')
        self.get_logger().info(f'[{self.mavros_ns}] mode set to {self.guided_mode}')

        if self.arm_before_auto:
            arm_request = CommandBool.Request()
            arm_request.value = True
            self._call_and_check(self.arming_client, arm_request, 'arming')
            self.get_logger().info(f'[{self.mavros_ns}] vehicle armed')

        auto_request = SetMode.Request()
        auto_request.custom_mode = self.auto_mode
        self._call_and_check(self.mode_client, auto_request, 'auto mode switch')
        self.get_logger().info(f'[{self.mavros_ns}] mode set to {self.auto_mode}')
        self.get_logger().info(f'[{self.mavros_ns}] waypoint mission is running')


def main():
    rclpy.init()
    node = PlaneMission()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
