import rclpy
from rclpy.node import Node

from mavros_msgs.srv import CommandBool, SetMode, WaypointPush, WaypointSetCurrent, CommandTOL
from mavros_msgs.msg import Waypoint, State


class SinglePlaneMission(Node):

    def __init__(self):
        super().__init__('single_plane_mission')

        self.state = State()

        self.create_subscription(
            State,
            '/plane1/state',
            self.state_cb,
            10
        )

        self.arming_client = self.create_client(CommandBool, '/plane1/cmd/arming')
        self.mode_client = self.create_client(SetMode, '/plane1/set_mode')
        self.wp_client = self.create_client(WaypointPush, '/plane1/mission/push')
        self.set_current_client = self.create_client(WaypointSetCurrent, '/plane1/mission/set_current')
        self.takeoff_client = self.create_client(CommandTOL, '/plane1/cmd/takeoff')

        self.wait_for_services()
        self.run_mission()

    def state_cb(self, msg):
        self.state = msg

    def wait_for_services(self):
        self.get_logger().info("Waiting for services...")
        clients = [
            self.arming_client,
            self.mode_client,
            self.wp_client,
            self.set_current_client,
            self.takeoff_client
        ]
        for c in clients:
            while not c.wait_for_service(1.0):
                pass
        self.get_logger().info("All services ready!")

    def create_mission(self):
        wp_list = []

        def wp(cmd, lat, lon, alt):
            w = Waypoint()
            w.frame = 3
            w.command = int(cmd)
            w.is_current = False
            w.autocontinue = True
            w.x_lat = float(lat)
            w.y_long = float(lon)
            w.z_alt = float(alt)
            return w

        # HOME (dummy)
        home = wp(16, 38.3148, -76.5489, 0.0)
        home.is_current = True
        wp_list.append(home)

        # TAKEOFF
        wp_list.append(wp(22, 38.3148, -76.5489, 60.0))

        # NAV WAYPOINTS
        wp_list.append(wp(16, 38.3150, -76.5495, 60.0))
        wp_list.append(wp(16, 38.3155, -76.5500, 60.0))
        wp_list.append(wp(16, 38.3160, -76.5490, 60.0))

        return wp_list

    def run_mission(self):

        self.get_logger().info("Waiting for FCU...")
        while rclpy.ok() and not self.state.connected:
            rclpy.spin_once(self, timeout_sec=1.0)

        self.get_logger().info("Connected!")

        # Upload mission
        req = WaypointPush.Request()
        req.waypoints = self.create_mission()
        future = self.wp_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)

        self.get_logger().info("Mission uploaded!")

        # Reset mission
        set_req = WaypointSetCurrent.Request()
        set_req.wp_seq = 0
        future = self.set_current_client.call_async(set_req)
        rclpy.spin_until_future_complete(self, future)

        self.get_logger().info("Mission reset!")

        # GUIDED mode
        mode_req = SetMode.Request()
        mode_req.custom_mode = "GUIDED"
        future = self.mode_client.call_async(mode_req)
        rclpy.spin_until_future_complete(self, future)

        self.get_logger().info("GUIDED mode")

        # ARM
        arm_req = CommandBool.Request()
        arm_req.value = True
        future = self.arming_client.call_async(arm_req)
        rclpy.spin_until_future_complete(self, future)

        self.get_logger().info("Armed!")

        # 🔥 EXPLICIT TAKEOFF (CRITICAL FIX)
        takeoff_req = CommandTOL.Request()
        takeoff_req.altitude = 60.0
        takeoff_req.latitude = 38.3148
        takeoff_req.longitude = -76.5489

        future = self.takeoff_client.call_async(takeoff_req)
        rclpy.spin_until_future_complete(self, future)

        self.get_logger().info("Takeoff command sent!")

        # AUTO mode
        mode_req = SetMode.Request()
        mode_req.custom_mode = "AUTO"
        future = self.mode_client.call_async(mode_req)
        rclpy.spin_until_future_complete(self, future)

        self.get_logger().info("AUTO mode → Mission running 🚀")


def main():
    rclpy.init()
    node = SinglePlaneMission()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()