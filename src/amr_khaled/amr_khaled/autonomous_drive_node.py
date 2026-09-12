import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Int32
from geometry_msgs.msg import Twist

LINEAR_SPEED = 1.0
ANGULAR_SPEED = 0.8
STEP_DURATION = 1.0
ROTATE_360_DURATION = 6.0
OSCILLATE_PERIOD = 1.0

SEQUENCE_1 = [
    {'type': 'move', 'x': 0.0, 'y': LINEAR_SPEED, 'ang': 0.0, 'duration': STEP_DURATION},
    {'type': 'move', 'x': LINEAR_SPEED, 'y': 0.0, 'ang': 0.0, 'duration': STEP_DURATION},
    {'type': 'rotate360', 'duration': ROTATE_360_DURATION},
]

SEQUENCE_2 = [
    {'type': 'move', 'x': LINEAR_SPEED, 'y': 0.0, 'ang': 0.0, 'duration': STEP_DURATION},
    {'type': 'move', 'x': 0.0, 'y': LINEAR_SPEED, 'ang': 0.0, 'duration': STEP_DURATION},
    {'type': 'oscillate'},
]

SEQUENCE_3 = [
    {'type': 'move', 'x': LINEAR_SPEED, 'y': LINEAR_SPEED, 'ang': 0.0, 'duration': STEP_DURATION * 1.5},
    {'type': 'oscillate'},
]

MODE_AUTO = 'AUTO'
MODE_MANUAL = 'MANUAL'


class AutonomousDriveNode(Node):
    def __init__(self):
        super().__init__('autonomous_drive_node')

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.mode_pub = self.create_publisher(String, '/drive_mode', 10)
        self.mode_sub = self.create_subscription(String, '/drive_mode', self.mode_callback, 10)
        self.key_sub = self.create_subscription(Int32, '/key_input', self.key_callback, 10)

        self.mode = MODE_AUTO
        self.sequence = None
        self.step_index = 0
        self.step_start_time = None

        self.create_timer(0.1, self.run_sequence)

        self.get_logger().info('Autonomous node ready | 1/2/3: sequence | M: toggle mode')

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
        if self.mode != MODE_AUTO:
            self.sequence = None
            self.send(0.0, 0.0, 0.0)

    def start_sequence(self, sequence):
        self.sequence = sequence
        self.step_index = 0
        self.step_start_time = self.get_clock().now()

    def advance_step(self):
        self.step_index += 1
        self.step_start_time = self.get_clock().now()
        if self.step_index >= len(self.sequence):
            self.sequence = None
            self.send(0.0, 0.0, 0.0)

    def key_callback(self, msg):
        key = msg.data

        if key == ord('m'):
            self.set_mode(MODE_MANUAL if self.mode == MODE_AUTO else MODE_AUTO)
            return

        if self.mode != MODE_AUTO:
            return

        if key == ord('1'):
            self.start_sequence(SEQUENCE_1)
        elif key == ord('2'):
            self.start_sequence(SEQUENCE_2)
        elif key == ord('3'):
            self.start_sequence(SEQUENCE_3)

    def run_sequence(self):
        if self.mode != MODE_AUTO or self.sequence is None:
            return

        step = self.sequence[self.step_index]
        elapsed = (self.get_clock().now() - self.step_start_time).nanoseconds / 1e9

        if step['type'] == 'move':
            if elapsed < step['duration']:
                self.send(step['x'], step['y'], step['ang'])
            else:
                self.advance_step()

        elif step['type'] == 'rotate360':
            if elapsed < step['duration']:
                self.send(0.0, 0.0, ANGULAR_SPEED)
            else:
                self.advance_step()

        elif step['type'] == 'oscillate':
            phase = int(elapsed / OSCILLATE_PERIOD)
            direction = ANGULAR_SPEED if phase % 2 == 0 else -ANGULAR_SPEED
            self.send(0.0, 0.0, direction)


def main():
    rclpy.init()
    node = AutonomousDriveNode()

    try:
        rclpy.spin(node)
    finally:
        node.send(0.0, 0.0, 0.0)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()