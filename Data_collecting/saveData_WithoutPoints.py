#!/usr/bin/env python3
from __future__ import print_function
from ctypes import sizeof
import sys
import rospy
import cv2
from std_msgs.msg import String
from sensor_msgs.msg import Image
from sensor_msgs.msg import PointCloud2
from sensor_msgs.msg import CameraInfo
from cv_bridge import CvBridge, CvBridgeError
import os
import pandas as pd 
import numpy as np
import open3d as o3d

# Saving without data loss
np.set_printoptions(threshold=sys.maxsize)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', 1000)

part_num = 1
counter = 0

def CreatePointCloud(RGB_PATH, DEPTH_PATH):
    color_raw = o3d.io.read_image(RGB_PATH) # Reads RGB image
    depth_npy = np.load(DEPTH_PATH) # Reads Depth data
    depth_raw  = o3d.geometry.Image(depth_npy) # Converts depth data into image format
    rgbd_image = o3d.geometry.RGBDImage.create_from_tum_format(color_raw, depth_raw) # Creates RGBD image using TUM format
    PointCloud = o3d.geometry.PointCloud.create_from_rgbd_image(
      rgbd_image,o3d.camera.PinholeCameraIntrinsic(o3d.camera.PinholeCameraIntrinsicParameters.PrimeSenseDefault)) # Creates Point Cloud from rgbd image
    PointCloud.transform([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]) # Flip it, otherwise the pointcloud will be upside down
    return PointCloud

class image_converter:
  def __init__(self):
    self.bridge = CvBridge()
    self.sub_RGB = rospy.Subscriber("/camera/color/image_raw",Image, self.callbackRGB)
    self.sub_DEPTH = rospy.Subscriber("/camera/depth/image_raw", Image, self.callbackDEPTH)
    self.subINFO_RGB = rospy.Subscriber("/camera/color/camera_info", CameraInfo, self.callbackINFO_RGB)
    self.subINFO_DEPTH = rospy.Subscriber("/camera/depth/camera_info", CameraInfo, self.callbackINFO_DEPTH)

  def callbackDEPTH(self, data):
    global img_DPH
    try:
      img_DPH = self.bridge.imgmsg_to_cv2(data, "32FC1")
    except CvBridgeError as e:
      print(e)


  def callbackRGB(self, data):
    global img_RGB
    try:
      img_RGB = self.bridge.imgmsg_to_cv2(data, "bgr8")
      img_RGB_copy = img_RGB.copy()

    except CvBridgeError as e:
      print(e)

    cv2.putText(img_RGB_copy, 'IMAGE: %d'%counter, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (0, 0, 255), 1, cv2.LINE_AA)
    cv2.putText(img_RGB_copy, 'PART: %d'%part_num, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.6, (0, 255, 255), 1, cv2.LINE_AA)

    key = cv2.waitKey(1)
    cv2.imshow('Gotta Catch ‘Em All!', img_RGB_copy)

    if key == ord('s'):
      SaveImg()
    if key == ord('p'):
      rospy.signal_shutdown("Exit")

      
  def callbackINFO_RGB(self, data):
    global imgI_RGB
    try:
      imgI_RGB = data
    except CvBridgeError as e:
      print(e)
      
  def callbackINFO_DEPTH(self, data):
    global imgI_DPH
    try:
      imgI_DPH = data
    except CvBridgeError as e:
      print(e)

def SaveImg():
  global counter, part_num, axis_points, object_name
  axis_points = [[0,0,0] , [0,0,0]]
  if(part_num == 1):
    cv2.imwrite('files/images/rgb_img_I/RGB%05d.png'%counter, img_RGB)
    np.save('files/images/depth_img_I/D%05d'%counter, img_DPH)
    part_num = 2
    PC = CreatePointCloud('files/images/rgb_img_I/RGB%05d.png'%counter, 'files/images/depth_img_I/D%05d.npy'%counter)
    o3d.visualization.draw_geometries([PC])

    print("First image was taken")
  else:
    cv2.imwrite('files/images/rgb_img_II/RGB%05d.png'%counter, img_RGB)
    np.save('files/images/depth_img_II/D%05d'%counter, img_DPH)
    np.save('files/cam_info/INFO%05d'%counter, imgI_RGB)
    part_num = 1

    PC = CreatePointCloud('files/images/rgb_img_II/RGB%05d.png'%counter, 'files/images/depth_img_II/D%05d.npy'%counter)
    o3d.visualization.draw_geometries([PC])
    print("Second image was taken")

    object_name = input("Instert object name: ")
    CollectData()
    counter += 1

def CollectData():
  global counter
  df = pd.DataFrame(
    [
      [
        object_name,
        'files/images/rgb_img_I/RGB%05d.png'%counter, 
        'files/images/rgb_img_II/RGB%05d.png'%counter, 
        'files/images/depth_img_I/D%05d.npy'%counter,
        'files/images/depth_img_II/D%05d.npy'%counter,
        'files/cam_info/INFO%05d.npy'%counter, 
        np.asarray(axis_points[0][0]),
        np.asarray(axis_points[0][1]),
        np.asarray(axis_points[0][2]),
        np.asarray(axis_points[1][0]),
        np.asarray(axis_points[1][1]),
        np.asarray(axis_points[1][2]),
      ]
    ],
    columns=
    [
      "object_name", "rgb_img_I", "rgb_img_II", "depth_img_I", "depth_img_II", "camera_info", "x1", "y1", "z1", "x2", "y2", "z2"
    ]
  )
 

  # create data.csv file if not exists
  if not os.path.isfile('files/data.csv'):
    df.to_csv('files/data.csv', index=False)
  else: # else it exists so append without header
    print('jest')
    df.to_csv('files/data.csv', mode='a', header=False, index=False)

def SET_counter():
  global counter
  csv_file = pd.read_csv('files/data.csv')
  last_element = csv_file["rgb_img_I"].iloc[-1]
  num = ""
  for c in last_element:
      if c.isdigit():
          num = num + c
  counter = int(num) + 1

def main(args):
  if os.path.isfile('files/data.csv'):
    SET_counter()

  ic = image_converter()
  rospy.init_node('image_converter', anonymous=True)

  try:
    rospy.spin()
  except KeyboardInterrupt:
    print("Shutting down")


if __name__ == '__main__':
    main(sys.argv)

