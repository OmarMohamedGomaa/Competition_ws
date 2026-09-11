import sys
import select
import termios
import tty
import cv2
from cv_bridge import CvBridge , CvBridgeError
import rclpy
from rclpy.node import Node 

from sensor_msgs.msg import Image
from ultralytics import YOLO

CONF_THRESHOLD = 0.6
class eyes_node(Node):
    def __init__(self):
        super().__init__('eyes_node')
        self.sub = self.create_subscription(Image, '/mono/image',self.camera_callback, 10)
        self.bridge = CvBridge()
        self.model = YOLO("/home/omar/amrws/src/amr_khaled/amr_khaled/real_or_fake_model .pt")
        self.detected = False
    def camera_callback(self,msg:Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg,desired_encoding='GRAY')
            if self.classify_image(cv_image) == "real":
                self.detected = True
                self.get_logger().error(f"seeing real")
            else:
                self.detected = False
                self.get_logger().error(f"seeing fake")
            
        except CvBridgeError as e:
            self.get_logger().error(f"camera error{e}")
    
            
    
    def classify_image(self,image_path, conf_threshold=CONF_THRESHOLD):
        result = self.model(image_path, verbose=False)[0]
        top1_idx = result.probs.top1
        top1_conf = float(result.probs.top1conf)
        predicted_label = result.names[top1_idx]

        if top1_conf < conf_threshold:
            return 'fake', top1_conf  # low-confidence -> forced fake
        return predicted_label
def main():
    rclpy.init()

    node = eyes_node()

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