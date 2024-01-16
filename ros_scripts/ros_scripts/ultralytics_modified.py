#!/usr/bin/python3
import rospy
from rospy.numpy_msg import numpy_msg
import numpy as np
from ultralytics import YOLO
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Header
import cv2
from sensor_msgs.msg import CameraInfo
import cProfile
import rospy
import moveit_commander
import geometry_msgs.msg
import sys
from geometry_msgs.msg import PoseStamped
from tf.transformations import quaternion_from_euler, euler_from_quaternion
from math import pi


from std_msgs.msg import Float64MultiArray


def profileit(name):
   def inner(func):
       def wrapper(*args, **kwargs):
           prof = cProfile.Profile()
           retval = prof.runcall(func, *args, **kwargs)
           # Note use of name from outer scope
           prof.dump_stats(name)
           return retval
       return wrapper
   return inner




class camera_detect:
   def __init__(self):
       self.bridge = CvBridge()
       self.model = YOLO('yolov5lu.pt')
       self.cv_image = None
       self.result = None
       self.class_names = None
       self.boxes = None
       self.info = None
       self.distance = None
       self.c1_time_stamp = None
       self.c2_time_stamp = None
       self.Center_x = None # x coordinate of bounding box center
       self.Center_y = None # y coordinate of bounding box center
       self.color_image_height = None #Height of opencv color image
       self.color_image_width = None #Width of opencv color image
       self.ll=[]
       self.obj_found = False
       self.image=None
       self.camera_intrinsics=None
       self.depth_img=None
       self.R = np.array([[0, 1, 0],
                     [0, 0, -1],
                     [-1, 0, 0]])
       self.camera_matrix = None


       self.the_points = Float64MultiArray()


       self.pub = rospy.Publisher("/the_points", Float64MultiArray, queue_size=1, latch=True)
       
       #################################################################
       
       self.robot = moveit_commander.RobotCommander()
       self.scene = moveit_commander.PlanningSceneInterface()
       self.group_name = "manipulator_left"
       self.move_group = moveit_commander.MoveGroupCommander(self.group_name)
       self.current_pose = self.move_group.get_current_pose().pose
       self.current_quaternion = [self.current_pose.orientation.x, self.current_pose.orientation.y, self.current_pose.orientation.z, self.current_pose.orientation.w]
       self.current_euler = euler_from_quaternion(self.current_quaternion)
       self.current_position = [self.current_pose.position.x, self.current_pose.position.y, self.current_pose.position.z]
       self.target_pose = geometry_msgs.msg.Pose()       
       
       

   def move_up(self):
       self.current_pose = self.current_pose
       self.target_pose.position.z = (self.current_pose.position.z + 0.05)
       
   def move_down(self):
       self.current_pose = self.current_pose
       self.target_pose.position.z = (self.current_pose.position.z - 0.05)
   def move_left(self):
       self.current_pose = self.current_pose
       self.target_pose.position.y = (self.current_pose.position.y - 0.05)
   def move_right(self):
       self.current_pose = self.current_pose
       self.target_pose.position.y = (self.current_pose.position.z + 0.05)
       
   def set_deltas(self):
       self.delta_x = (self.Center_x - (self.cv_image.shape[1] // 2))
       self.delta_y = (self.Center_y - (self.cv_image.shape[0] // 2))   
       
  def move_conditions_x(self):
       if self.delta_x < 0:
           self.move_right()
       elif self.delta_x > 0:
           self.move_left()
   
   def move_conditions_y(self):
       if self.delta_y < 0:
           self.move_down()
       elif self.delta_y > 0:
           self.move_up()
       
       
   def move_arms(self):
       self.set_deltas()
       self.move_conditions_x()
       self.move_conditions_y()
       self.move_group.set_pose_target(self.target_pose)
       self.move_group.set_max_velocity_scaling_factor(0.01)
       plan = self.move_group.go(wait=True)
       if plan:
           rospy.loginfo("Motion planning and execution succeeded!")
       else:
           rospy.logerr("Motion planning and execution failed!")

       	
       
#######################################################################   

   def callback0(self,msg):
       self.camera_intrinsics = msg
       self.camera_matrix = np.array(self.camera_intrinsics.K).reshape(3, 3)




   def callback1(self,msg):
       self.image = msg




   def callback2(self, msg):
       self.depth_img=msg
 
   
   
   def calc(self):
       #print("CALLBACK2")
       try:
           self.c1_time_stamp = self.image.header.stamp
           self.c2_time_stamp = self.depth_img.header.stamp
           time1 = rospy.Time(self.c1_time_stamp.secs, self.c1_time_stamp.nsecs)
           time2 = rospy.Time(self.c2_time_stamp.secs, self.c2_time_stamp.nsecs)
           time_diff = (time2 - time1).to_sec()
       except:
           pass
       try:
           if abs(time_diff)<0.9:
               print("TIME_DIFF: ",time_diff)
               self.cv_image = self.bridge.imgmsg_to_cv2(self.image, desired_encoding='rgb8')
               self.result = self.model(self.cv_image, verbose=True)[0]
               self.boxes = self.result.boxes.data.cpu().numpy()
               if len(self.boxes) > 0:
                   depth_image = self.bridge.imgmsg_to_cv2(self.depth_img, desired_encoding='16UC1')
                   print([self.cv_image.shape[0],self.cv_image.shape[1],depth_image.shape[0],depth_image.shape[1]])
                   scale_factor_col = depth_image.shape[1] / self.cv_image.shape[1]
                   scale_factor_row = depth_image.shape[0] / self.cv_image.shape[0]
                   self.class_names = self.result.names
                   try:
                       for i in range(len(self.boxes)):
                           class_index = int(self.boxes[i][5])
                           #class_name =
                           #self.obj_found = True
                           self.info = self.boxes[i][0:4]
                           #print(self.boxes[i])
                           self.Center_x = self.info[0]+(self.info[2]-self.info[0])/ 2
                           self.Center_y = self.info[1]+(self.info[3] - self.info[1])/ 2
                           col = int(self.Center_x * scale_factor_col)
                           row = int(self.Center_y  * scale_factor_row)
                           #print("ROW: ", row," COl: ", col)
                           if str(self.class_names[class_index]) == "bottle": #or str(self.class_names[class_index]) == "person":


                               self.distance = depth_image[row][col]/1000


                               distortion_coeffs = np.array(self.camera_intrinsics.D)
                               undistorted_coords = cv2.undistortPoints(np.array([(col, row)], dtype=np.float32),
                                                                        self.camera_matrix, distortion_coeffs)
                               undistorted_x = undistorted_coords[0, 0, 0]
                               undistorted_y = undistorted_coords[0, 0, 1]
                               #print("DISTANCE of ", str(self.class_names[class_index]), ": ", self.distance, "\n")
                               x_ndc = (undistorted_x - self.camera_intrinsics.K[2]) / self.camera_intrinsics.K[0]
                               y_ndc = (undistorted_y - self.camera_intrinsics.K[5]) / self.camera_intrinsics.K[4]
                               x_cam = x_ndc * (self.distance) / 1.0
                               y_cam = y_ndc * (self.distance) / 1.0


                               print("CLASS_NAME: ", str(self.class_names[class_index]), " ,POINT: ",[x_cam ,y_cam,self.distance])
                               self.the_points.data= [x_cam ,y_cam,self.distance]
                               self.pub.publish(self.the_points)








                   except IndexError:
                       pass
                       print("INDEX ERROR \n")


           #else:
           #    print("SLOW")
       except UnboundLocalError:
           pass
       #prof.disable()
       #prof.print_stats()"""


   def detect(self):
       rospy.Subscriber("/realsense/color/image_raw", Image, self.callback1, queue_size=100, buff_size=2_000_000)


   def detect_depth(self):
       rospy.Subscriber("/realsense/depth/image_rect_raw", Image, self.callback2, queue_size=100, buff_size=2_000_000)


   def show_video(self):
       rospy.Subscriber("/camera/depth/camera_info", CameraInfo, self.callback0, queue_size=1)


#@profileit("/home/philip/Desktop/output.txt")
def main():


       rospy.init_node("test_node_1")
       tester = camera_detect()
       #tester.camera_intrinsics = rospy.wait_for_message("/camera/depth/camera_info", CameraInfo)


       rospy.Subscriber("/realsense/depth/camera_info", CameraInfo, tester.callback0, queue_size=100)
       rospy.Subscriber("/realsense/color/image_raw", Image, tester.callback1, queue_size=1, buff_size=2_000_000)
       rospy.Subscriber("/realsense/depth/image_rect_raw", Image, tester.callback2, queue_size=1, buff_size=2_000_000)


       while not rospy.is_shutdown():
           tester.calc()
           tester.move_arms()
       #tester.detect()
       #tester.detect_depth()


       #rospy.spin()


   #except rospy.ROSInterruptException:
   #    pass




if __name__ == "__main__":
   main()


