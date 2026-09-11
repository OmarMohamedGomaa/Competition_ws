import json

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Int32
from cv_bridge import CvBridge
from ultralytics import YOLO

MODEL_PATH = '/home/robot/models/scroll_detector.pt'
CONFIDENCE_THRESHOLD = 0.6


class ScrollDetectionNode(Node):
    def __init__(self):
        super().__init__('scroll_detection_node')

        self.bridge = CvBridge()

        self.get_logger().info('Loading model: ' + MODEL_PATH)
        self.model = YOLO(MODEL_PATH)
        self.get_logger().info('Model loaded.')

        self.seen_class_ids = set()

        self.create_subscription(Image, '/mono/image', self.image_callback, 10)

        self.detections_pub = self.create_publisher(String, '/scroll_detections', 10)
        self.count_pub = self.create_publisher(Int32, '/scrolls_found_count', 10)

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        results = self.model(frame, verbose=False)
        detections = []

        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < CONFIDENCE_THRESHOLD:
                    continue

                class_id = int(box.cls[0])
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]

                detections.append({
                    'class_id': class_id,
                    'confidence': confidence,
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                })
                self.seen_class_ids.add(class_id)

        detections_msg = String()
        detections_msg.data = json.dumps(detections)
        self.detections_pub.publish(detections_msg)

        count_msg = Int32()
        count_msg.data = len(self.seen_class_ids)
        self.count_pub.publish(count_msg)

def main():
    rclpy.init()
    node = ScrollDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
