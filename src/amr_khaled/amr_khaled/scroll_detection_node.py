import os
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from cv_bridge import CvBridge
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory
MODEL_PATH = os.path.join(get_package_share_directory('amr_khaled'), 'real_or_fake_model.pt')
CONFIDENCE_THRESHOLD = 0.9


class ScrollDetectionNode(Node):
    def __init__(self):
        super().__init__('scroll_detection_node')

        self.bridge = CvBridge()

        self.get_logger().info('Loading model: ' + MODEL_PATH)
        # self.model = YOLO(MODEL_PATH)
        self.get_logger().info('Model loaded.')

        self.detected = False

        self.create_subscription(Image, '/mono/image', self.image_callback, 10)


    def image_callback(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        color = self.classify_dominant_color(frame)
        # frame = cv2.
        # result = self.model(frame, verbose=False)[0]
        # top1_idx = result.probs.top1
        # top1_conf = float(result.probs.top1conf)
        predicted_label = "real" if color == "blue" else "fake"

        self.detected = (predicted_label == 'real')
        if color == "neither":
            predicted_label = "none"
  

        self.get_logger().info(f'(label={predicted_label}')


        self.show_frame(frame, predicted_label, 0.67)


    def classify_dominant_color(self,bgr_image, min_fraction=0.20):

        hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)

        # Red wraps around the HSV hue circle (0-10 and 170-180)
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

        # Blue hue range
        lower_blue = np.array([100, 70, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        total_pixels = bgr_image.shape[0] * bgr_image.shape[1]
        red_fraction = cv2.countNonZero(red_mask) / total_pixels
        blue_fraction = cv2.countNonZero(blue_mask) / total_pixels

        if red_fraction < min_fraction and blue_fraction < min_fraction:
            return 'neither'
        return 'red' if red_fraction >= blue_fraction else 'blue'
    def show_frame(self, frame, predicted_label, top1_conf):
        # Convert to BGR so overlay text/color renders correctly (frame is mono8/grayscale)
        display_frame = frame

        color = (255 , 255, 255)
        if predicted_label == "real":
            color = (0,255,0)
        elif predicted_label == "fake":
            color = (0,0,255)  
        text = f'{predicted_label} '

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