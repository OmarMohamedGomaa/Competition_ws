import cv2
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from ultralytics import YOLO

MODEL_PATH = '/home/robot/models/scroll_detector.pt'
CONFIDENCE_THRESHOLD = 0.6
MIN_SAFE_DISTANCE = 0.15

LINEAR_SPEED = 1.0
ANGULAR_SPEED = 0.8
STEP_DURATION = 0.6
ROTATE_360_DURATION = 6.0
OSCILLATE_PERIOD = 1.0

KEY_MOVES = {
    ord('w'): (LINEAR_SPEED, 0.0, 0.0),
    ord('s'): (-LINEAR_SPEED, 0.0, 0.0),
    ord('a'): (0.0, LINEAR_SPEED, 0.0),
    ord('d'): (0.0, -LINEAR_SPEED, 0.0),
    ord('q'): (0.0, 0.0, ANGULAR_SPEED),
    ord('e'): (0.0, 0.0, -ANGULAR_SPEED),
}

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


class DriveNode(Node):
    def __init__(self):
        super().__init__('controller_node')

        self.bridge = CvBridge()
        

        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub = self.create_subscription(Image, '/mono/image', self.image_callback, 10)
        self.distance_sub = self.create_subscription(
            Float32, '/ultrasonic_distance', self.distance_callback, 10)

        self.latest_distance = None

        self.mode = MODE_AUTO

        self.sequence = None
        self.step_index = 0
        self.step_start_time = None

        self.active_key = None
        self.move_end_time = None

        self.get_logger().info(
            'Starting in AUTO | 1/2/3: sequence | M: toggle mode | O: stop | P: abort')

    def distance_callback(self, msg):
        self.latest_distance = msg.data

    def too_close(self):
        return self.latest_distance is not None and self.latest_distance < MIN_SAFE_DISTANCE

    def send(self, x, y, ang):
        if self.too_close() and (x > 0.0 or y != 0.0):
            self.get_logger().warn(f'Too close ({self.latest_distance:.2f} m), blocking motion')
            x, y = 0.0, 0.0

        msg = Twist()
        msg.linear.x = x
        msg.linear.y = y
        msg.angular.z = ang
        self.pub.publish(msg)

    def set_mode(self, mode):
        self.mode = mode
        self.sequence = None
        self.active_key = None
        self.send(0.0, 0.0, 0.0)
        self.get_logger().info(f'Mode: {mode}')

    def detect_scroll(self, frame):
        results = self.model(frame, verbose=False)
        for result in results:
            for box in result.boxes:
                if float(box.conf[0]) >= CONFIDENCE_THRESHOLD:
                    return True
        return False

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

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        cv2.imshow('Mono Camera - Drive', frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('p'):
            self.send(0.0, 0.0, 0.0)
            rclpy.shutdown()
            return

        if key == ord('o'):
            self.sequence = None
            self.active_key = None
            self.send(0.0, 0.0, 0.0)
            return

        if key == ord('m'):
            new_mode = MODE_MANUAL if self.mode == MODE_AUTO else MODE_AUTO
            self.set_mode(new_mode)
            return

        if self.mode == MODE_AUTO:
            self.run_auto(frame, key)
        else:
            self.run_manual(key)

    def run_auto(self, frame, key):
        if key == ord('1'):
            self.start_sequence(SEQUENCE_1)
            return
        if key == ord('2'):
            self.start_sequence(SEQUENCE_2)
            return
        if key == ord('3'):
            self.start_sequence(SEQUENCE_3)
            return

        if self.detect_scroll(frame):
            self.get_logger().info('Scroll detected')
            self.sequence = None
            self.send(0.0, 0.0, 0.0)
            return

        if self.sequence is None:
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

    def run_manual(self, key):
        now = self.get_clock().now()

        if key in KEY_MOVES and key != self.active_key:
            self.active_key = key
            self.move_end_time = now + Duration(seconds=STEP_DURATION)
            x, y, ang = KEY_MOVES[key]
            self.send(x, y, ang)
            return

        if self.active_key is not None and now >= self.move_end_time:
            self.active_key = None
            self.send(0.0, 0.0, 0.0)


def main():
    rclpy.init()
    node = DriveNode()

    try:
        rclpy.spin(node)
    finally:
        node.send(0.0, 0.0, 0.0)
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()