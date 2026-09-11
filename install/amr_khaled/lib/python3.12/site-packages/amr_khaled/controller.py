import sys
import select
import termios
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

LINEAR_SPEED = 1.0
ANGULAR_SPEED = 0.8


class TeleopNode(Node):
    def __init__(self):
        super().__init__('wasd_teleop_node')

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        self.manual_mode = True

        self.timer = self.create_timer(0.1, self.control)

        self.get_logger().info('Manual mode')
        self.get_logger().info('w/a/s/d to drive')
        self.get_logger().info('m to switch mode, x to stop, q to quit')

    def send(self, linear, angular):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.pub.publish(twist)

    def get_key(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)

        return None

    def control(self):
        key = self.get_key()

        if key == ('q' or 'Q'):
            self.send(0.0, 0.0)
            rclpy.shutdown()
            return

        if key == ('m' or 'M'):
            self.manual_mode = not self.manual_mode
            self.send(0.0, 0.0)

            if self.manual_mode:
                self.get_logger().info('Manual mode')
            else:
                self.get_logger().info('Autonomous mode')

            return

        if key == ('x' or 'X'):
            self.send(0.0, 0.0)
            return

        if self.manual_mode:
            if key == ('w' or 'W'):
                self.send(LINEAR_SPEED, 0.0)

            elif key == ('s' or 'S'):
                self.send(-LINEAR_SPEED, 0.0)

            elif key == ('a' or 'A'):
                self.send(0.0, ANGULAR_SPEED)

            elif key == ('d' or 'D'):
                self.send(0.0, -ANGULAR_SPEED)
            else:
                self.send(0.0, 0.0)

        else:
            self.send(LINEAR_SPEED, 0.0)

def main():
    rclpy.init()

    node = TeleopNode()

    old = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    try:
        rclpy.spin(node)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        node.send(0.0, 0.0)
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()