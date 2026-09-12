import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import String, Int32
from geometry_msgs.msg import Twist

LINEAR_SPEED = 1.0
ANGULAR_SPEED = 0.8
STEP_DURATION = 0.6

KEY_MOVES = {
    ord('w'): (LINEAR_SPEED, 0.0, 0.0),
    ord('s'): (-LINEAR_SPEED, 0.0, 0.0),
    ord('a'): (0.0, LINEAR_SPEED, 0.0),
    ord('d'): (0.0, -LINEAR_SPEED, 0.0),
    ord('q'): (0.0, 0.0, ANGULAR_SPEED),
    ord('e'): (0.0, 0.0, -ANGULAR_SPEED),
}

MODE_AUTO = 'AUTO'
MODE_MANUAL = 'MANUAL'


class ManualDriveNode(Node):
    def __init__(self):
        super().__init__('manual_drive_node')

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.mode_pub = self.create_publisher(String, '/drive_mode', 10)
        self.mode_sub = self.create_subscription(String, '/drive_mode', self.mode_callback, 10)
        self.key_sub = self.create_subscription(Int32, '/key_input', self.key_callback, 10)

        self.mode = MODE_AUTO
        self.active_key = None
        self.move_end_time = None

        self.create_timer(0.05, self.check_step_timeout)

        self.get_logger().info('Manual node ready | WASD: move | Q/E: rotate | O: stop | M: toggle | P: abort')

    def send(self, x, y, ang):
        msg = Twist()
        msg.linear.x = x
        msg.linear.y = y
        msg.angular.z = ang
        self.pub.publish(msg)
        self.get_logger().info(f'cmd_vel x={x:.2f} y={y:.2f} ang={ang:.2f}', throttle_duration_sec=0.5)

    def set_mode(self, mode):
        out = String()
        out.data = mode
        self.mode_pub.publish(out)

    def mode_callback(self, msg):
        self.mode = msg.data
        if self.mode != MODE_MANUAL:
            self.active_key = None
            self.send(0.0, 0.0, 0.0)

    def key_callback(self, msg):
        key = msg.data

        if key == ord('p'):
            self.send(0.0, 0.0, 0.0)
            rclpy.shutdown()
            return

        if key == ord('m'):
            self.set_mode(MODE_AUTO if self.mode == MODE_MANUAL else MODE_MANUAL)
            return

        if key == ord('o'):
            self.active_key = None
            self.send(0.0, 0.0, 0.0)
            return

        if self.mode != MODE_MANUAL:
            return

        if key in KEY_MOVES and key != self.active_key:
            self.active_key = key
            self.move_end_time = self.get_clock().now() + Duration(seconds=STEP_DURATION)
            x, y, ang = KEY_MOVES[key]
            self.send(x, y, ang)

    def check_step_timeout(self):
        if self.active_key is not None and self.get_clock().now() >= self.move_end_time:
            self.active_key = None
            self.send(0.0, 0.0, 0.0)


def main():
    rclpy.init()
    node = ManualDriveNode()

    try:
        rclpy.spin(node)
    finally:
        node.send(0.0, 0.0, 0.0)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()