import sys
import select
import termios
import tty

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class EyesNode(Node):
    def __init__(self):
        super().__init__('eyes_node')

        self.key_pub = self.create_publisher(Int32, '/key_input', 10)
        self.create_timer(0.05, self.check_key)

        self.get_logger().info('Eyes node ready (terminal input, no camera)')

    def get_key(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return ord(sys.stdin.read(1))
        return None

    def check_key(self):
        key = self.get_key()
        if key is not None:
            out = Int32()
            out.data = key
            self.key_pub.publish(out)
            self.get_logger().info(f'Key published: {chr(key)!r}')


def main():
    rclpy.init()
    node = EyesNode()

    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    try:
        rclpy.spin(node)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()