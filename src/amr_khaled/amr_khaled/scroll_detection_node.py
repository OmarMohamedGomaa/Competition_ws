import os
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from cv_bridge import CvBridge
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory
MODEL_PATH = os.path.join(get_package_share_directory('amr_khaled'), 'real_or_fake_model.pt')
CONFIDENCE_THRESHOLD = 0.6


class ScrollDetectionNode(Node):
    def __init__(self):
        super().__init__('scroll_detection_node')

        self.bridge = CvBridge()

        self.get_logger().info('Loading model: ' + MODEL_PATH)
        self.model = YOLO(MODEL_PATH)
        self.get_logger().info('Model loaded.')

        self.detected = False

        self.create_subscription(Image, '/mono/image', self.image_callback, 10)


    def image_callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg.data, desired_encoding='mono8')

        result = self.model(frame, verbose=False)[0]
        top1_idx = result.probs.top1
        top1_conf = float(result.probs.top1conf)
        predicted_label = result.names[top1_idx]

        self.detected = (predicted_label == 'real')
        if top1_conf < CONFIDENCE_THRESHOLD:
            predicted_label = "none"
  

        self.get_logger().info(f'(label={predicted_label}, conf={top1_conf:.2f})')


        self.show_frame(frame, predicted_label, top1_conf)

    def show_frame(self, frame, predicted_label, top1_conf):
        # Convert to BGR so overlay text/color renders correctly (frame is mono8/grayscale)
        display_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        color = (0, 255, 0) if self.detected else (0, 0, 255)  # green if real+confident, red otherwise
        text = f'{predicted_label} ({top1_conf:.2f})'

        cv2.putText(display_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, color, 2, cv2.LINE_AA)

        cv2.imshow('Scroll Detection - Camera Feed', display_frame)
        cv2.waitKey(1)  # required for OpenCV to refresh the window; 1ms, non-blocking

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()

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