import sys, os, time, warnings

paths = ['/Users/billymazotti/miniforge3/lib/python3.9/site-packages/',
         os.getcwd()]

for path in paths:
    sys.path.append(path)

import bpy
import numpy as np
import cv2
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
import json


import random
import math
from math import pi
from mathutils import Euler, Color, Vector
from pathlib import Path
from datetime import datetime


# Make sure changes to local functions are being accounted for
import rotated_rect
from importlib import reload
reload(rotated_rect)
from rotated_rect import RRect_center
import copy



def selectRandomCameraTarget():
    
    # collect list of all targets
    target_list = []
    for obj in bpy.data.objects:
        if obj.name.split("_")[0] == "CameraTarget":
            target_list.append(obj.name)
    
    selected_target = random.choice(target_list)

    return selected_target
    
        
def positionCamera(x_pos, y_pos, z_pos, roll_deg):
    """
    Moves the CameraTarget Object 
    """
    bpy.data.objects["Camera"].select_set(True)
    current_state = bpy.data.objects["Camera"].select_get()
    bpy.context.view_layer.objects.active = bpy.data.objects['Camera']

    # position camera to specified x,y,z location
    bpy.data.objects["Camera"].location = [x_pos, y_pos, z_pos]
    
    # select camera target
    camera_target_name = selectRandomCameraTarget()
    
    # set specific axis to point up
    bpy.ops.object.constraint_add(type='TRACK_TO')
    bpy.data.objects["Camera"].constraints["Track To"].target = bpy.data.objects[camera_target_name]
    bpy.data.objects["Camera"].constraints["Track To"].up_axis = 'UP_Y'
    bpy.ops.constraint.apply(constraint="Track To", owner='OBJECT')

    # save the upright angle
    upright_camera_orientation = bpy.data.objects["Camera"].rotation_euler
    bpy.context.scene.transform_orientation_slots[0].type = 'GLOBAL'
    upright_camera_orientation = bpy.data.objects["Camera"].rotation_euler
    
    # delete TRACK_TO constraint to allow for camera roll
    bpy.ops.constraint.delete(constraint="Track To", owner='OBJECT')
    bpy.data.objects["Camera"].rotation_euler = upright_camera_orientation
    
    # add roll to camera
    bpy.data.objects["Camera"].rotation_mode = 'ZYX'
    bpy.data.objects["Camera"].rotation_euler[2] = upright_camera_orientation[2] + \
                                                        roll_deg*pi/180



def placeCameraInVolume(cubeMeshName,roll):
    """
    randomly place camera in an UNROTATED mesh cube primitive
    
    cube primite cannot be rotated, only changed in scale and location
    """
    
    # define the x,y,z limits of the cube mesh
    centroidXYZ = np.array(bpy.data.objects[cubeMeshName].location)
    dimensionsXYZ = np.array(bpy.data.objects[cubeMeshName].dimensions)
    camera_volume_limits = centroidXYZ * np.ones((2,3))
    camera_volume_limits[0,:] -= dimensionsXYZ/2
    camera_volume_limits[1,:] += dimensionsXYZ/2

    camera_volume_limits_mm = (camera_volume_limits * 1000).astype(int)

    # genrate random x,y,z point within the volume for camera placement
    randX = random.randrange(start = camera_volume_limits_mm[0,0],
                            stop = camera_volume_limits_mm[1,0],
                            step = 1) / 1000
    randY = random.randrange(start = camera_volume_limits_mm[0,1],
                            stop = camera_volume_limits_mm[1,1],
                            step = 1) / 1000
    randZ = random.randrange(start = camera_volume_limits_mm[0,2],
                            stop = camera_volume_limits_mm[1,2],
                            step = 1) / 1000
    
    positionCamera(randX, randY, randZ, roll)

def generate_random_object_pose(object_plane_limits_mm,centroidXYZ,objects_dict,objectName):
    
    # genrate random x,y,z point on plane for object placement
    randX = random.randrange(start = object_plane_limits_mm[0,0],
                            stop = object_plane_limits_mm[1,0],
                            step = 1) / 1000
    randY = random.randrange(start = object_plane_limits_mm[0,1],
                            stop = object_plane_limits_mm[1,1],
                            step = 1) / 1000    
    z_pos = centroidXYZ[2]        
            
    # generate random orientation wihting rotaiton limits
    if (objects_dict[objectName]["rot_limits"][0][1] - \
            objects_dict[objectName]["rot_limits"][0][0] == 0):
        randX_theta = objects_dict[objectName]["rot_limits"][0][0]
    else:
        randX_theta = random.randrange(start = objects_dict[objectName]["rot_limits"][0][0],
                                        stop = objects_dict[objectName]["rot_limits"][0][1],
                                        step = 1)
    if (objects_dict[objectName]["rot_limits"][1][1] - \
            objects_dict[objectName]["rot_limits"][1][0] == 0):
        randY_theta = objects_dict[objectName]["rot_limits"][0][0]
    else:
        randY_theta = random.randrange(start = objects_dict[objectName]["rot_limits"][1][0],
                                        stop = objects_dict[objectName]["rot_limits"][1][1],
                                        step = 1)
    if (objects_dict[objectName]["rot_limits"][2][1] - \
            objects_dict[objectName]["rot_limits"][2][0] == 0):
        randZ_theta = objects_dict[objectName]["rot_limits"][0][0]
    else:
        randZ_theta = random.randrange(start = objects_dict[objectName]["rot_limits"][2][0],
                                        stop = objects_dict[objectName]["rot_limits"][2][1],
                                        step = 1)
        
    return randX, randY, z_pos, randX_theta, randY_theta, randZ_theta

def add_polygons(contour_of_interest,polygon_list):
    
    # add polygon if first
    if len(polygon_list) == 0:
        polygon_list += (contour_of_interest,)
        # print("First Polygon Accepted")
        return polygon_list, True
    
    # check to see if contour_of_interst intersects with any contours in polygon_list
    candidate_polygon = Polygon(contour_of_interest.reshape(-1,2))
    
    for i in range(len(polygon_list)):
        polygon_i = polygon_list[i].reshape(-1,2)
        
        ### DEBUGGING OCCLUSIONS
        # polygon_i_visual = np.vstack((polygon_i,polygon_i[0,:]))
        # coi_visual = contour_of_interest.reshape(-1,2)
        # coi_visual = np.vstack((coi_visual,coi_visual[0,:]))
        
        # plt.figure()
        # plt.plot(polygon_i[:,0],polygon_i[:,1])
        # plt.plot(coi[:,0],coi[:,1])
        # ax = plt.gca()
        # ax.set_aspect('equal', adjustable='box')
        # plt.savefig('test_image.png')
        
        if candidate_polygon.intersects(Polygon(polygon_i)):
            return polygon_list, False
    
    # if we looked through all polgons without intersection, add polygon to list
    polygon_list += (contour_of_interest,)
    return polygon_list, True

def placeObjectOnPlane(planeName, objectName, objects_dict, placed_object_footprints, max_attempts):
    """
        assmes object is small enough to fit in plane
        assumes object has local z vecotr pointing up 
        
        current errors:
            - roll grows exponentially
            
    """
    
    # set position to ensure object is not hanging off plane
    # define the x,y limits of the plane
    centroidXYZ = np.array(bpy.data.objects[planeName].location)
    planeDimensionsXYZ = np.array(bpy.data.objects[planeName].dimensions)
    
    # look through all subparts to find 
    objectDimensionsXYZ = np.array(bpy.data.objects[objectName].dimensions)
   
    max_object_diameter = max(objectDimensionsXYZ[0],objectDimensionsXYZ[1])
    
    # object_plane_limits = [[xmin,ymin],[xmax,ymax]]
    object_plane_limits = centroidXYZ[0:2] * np.ones((2,2))


    if (planeDimensionsXYZ[0:2] - max_object_diameter < 0.0).any():
       warnings.warn(f"Object Plane {planeName} is too small for object {objectName}. Increase size of object plane {planeName} or remove {objectName} from the plane's json file")
       return placed_object_footprints

        
    object_plane_limits[0,:] -= (planeDimensionsXYZ[0:2] - max_object_diameter)/2
    object_plane_limits[1,:] += (planeDimensionsXYZ[0:2] - max_object_diameter)/2
    
    
    object_plane_limits_mm = (object_plane_limits * 1000).astype(int)
    
    attempt_iter = 0
    while attempt_iter < max_attempts:
        # propose random object pose [m]
        randX, randY, z_pos, randX_theta, randY_theta, randZ_theta = \
            generate_random_object_pose(object_plane_limits_mm,centroidXYZ,objects_dict,objectName)
        
        # Compute Footprints
        (W_mm,H_mm) = (objectDimensionsXYZ[0]*1000,objectDimensionsXYZ[1]*1000)
        ang = -randZ_theta #degrees
        P0_mm = (randX*1000,randY*1000)
        rr = RRect_center(P0_mm,(W_mm,H_mm),ang)
        contour_mm = np.array([[[rr.verts[0][0],rr.verts[0][1]]],
                                [[rr.verts[1][0],rr.verts[1][1]]],
                                [[rr.verts[2][0],rr.verts[2][1]]],
                                [[rr.verts[3][0],rr.verts[3][1]]]])
        
        placed_object_footprints, new_polygon_added = add_polygons(contour_mm,placed_object_footprints)
        
        if new_polygon_added:
            # check to see if pose is valid with respect to currently placed objects
            bpy.data.objects[objectName].location = [randX, randY, z_pos]                             
            bpy.data.objects[objectName].rotation_euler = [randX_theta*math.pi/180,
                                                            randY_theta*math.pi/180,
                                                            randZ_theta*math.pi/180]
            # print(f"Iter {attempt_iter}: Accepted Polygon")
            break
        
        # print(f"Iter {attempt_iter}: Rejected Polygon")
        attempt_iter += 1
    
    return placed_object_footprints

def objects_in_fov():
    """
    Retern a list of all coco object namesg
    output:

    """
    
    camera = bpy.data.objects["Camera"]
    fov = camera.data.angle
    location = camera.location
    direction = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    visible_objects = [obj for obj in bpy.context.scene.objects if not obj.hide_render]

    
    # creeat list of all visible objects in fov
    objects_in_fov = []
    for obj in visible_objects:
        if obj.type != 'MESH' or not obj.visible_get(): 
            continue    # skip non mesh and non-visible objects
        if obj.name.split("_")[0] != 'obj':
            continue    # skip objects that don't start with obj_
        for v in obj.data.vertices:
            vertex_world = obj.matrix_world @ v.co
            to_vertex = vertex_world - location
            angle_to_vertex = direction.angle(to_vertex)
            if angle_to_vertex < fov / 2:
                objects_in_fov.append(obj.name)
                break

    objects_in_fov.sort()
    return objects_in_fov


def color_all_objects():
    
    visible_objects = [obj for obj in bpy.context.scene.objects if not obj.hide_render]
    objects_in_scene_names = []
    for obj in visible_objects:
        if obj.name.split("_")[0] == 'obj':
            objects_in_scene_names.append(obj.name)
    
    color_to_object_mapping = {}
    for IndexOB,obj in enumerate(objects_in_scene_names):
        IndexOB += 1
        bpy.data.objects[obj].pass_index = IndexOB
        color_to_object_mapping[IndexOB] = bpy.data.objects[obj].name
        
    return color_to_object_mapping
    
            
    

def annotate_2Dand_3D_data_of_in_view_objects():
    """
    Determine which objects are in view and are showing at least X pixels? in FOV?
    - Step 1: find all objects in fov using fov script (still could be occluded)
    - Step 2: create mask of each object in FOV and if there's at least 1 pixel then annotate the object
        https://www.youtube.com/watch?v=xeprI8hJAH8
    - Step 3: get the object's distance from the camera using object's centroid location 
        (make sure this is the actual centroid and not just the object's groudnign point) xyz data
    """
    
    
    # retreive objects in the field of view
    object_in_fov_names = objects_in_fov()
    print(object_in_fov_names)
    
    # assign pass index to each object
    for IndexOB,obj in enumerate(object_in_fov_names):
        IndexOB += 1
        bpy.data.objects[obj].pass_index = IndexOB
        
    
def move_away_all_objects(location):
    for obj in bpy.data.objects:
        if obj.name.split("_")[0] == "obj": 
            bpy.data.objects[obj.name].location = location
            bpy.data.objects[obj.name].rotation_euler[2] = 0.0

def relative_location(obj1_name, obj2_name):
    
    """
    inputs:
        obj1: primary object
        obj2: the object whose location we want with respect to obj1's local frame
    outputs:
        relative_location = [x, y, z]
    """
    cam = bpy.data.objects[obj1_name]
    obj = bpy.data.objects[obj2_name]
    mat_rel = cam.matrix_world.inverted() @ obj.matrix_world
    relative_location = np.array(mat_rel.translation)
    relative_location[2] *= -1  # invert z distance
    
    return relative_location  

def deselect_all_objects():
    """ Deselect all objects
    """
    # deselect all objects
    bpy.ops.object.select_all(action='DESELECT')  

def select_object(obj_name):
    """ Select a specific object; ensure that no other objecrts are
        selected

    Args:
        obj_name (string): name a object to be selected; found
                        using bpy.data.objects["object_name"].name
    """
    deselect_all_objects()
    # select object of interest
    bpy.data.objects[obj_name].select_set(True) 
    current_state = bpy.data.objects[obj_name].select_get()
    bpy.context.view_layer.objects.active = bpy.data.objects[obj_name]

def duplicate_object(obj_name):
    """ Duplicate an object; name should end with .###
        (e.g. if original object ot be duplicated is named "pepsi_can"
        then the duplicated object will have the name "pepsi_can.001")

    Args:
        obj_name (string): name a object to be duplicated

    Returns:
        string: name of the newly duplicated object
    """
    select_object(obj_name)
    bpy.ops.object.duplicate()
    new_object_name = bpy.context.selected_objects[0].name
    
    return new_object_name
    
def delete_all_duplicate_objects():
    """ Delete all duplicated objects in the entire Scene Collection
    
        Assumptions:
        - all objects to be deleted must have names starting with obj_
        - all original objects (non-duplicates) must not have a "." in 
        their names
        - all duplicates must have a since "." in their names
    """
    for obj in bpy.data.objects:
        if obj.name.split("_")[0] == 'obj' and len(obj.name.split("."))==2:
            select_object(obj.name)
            bpy.ops.object.delete()
                    
                    
def dictionary_for_object_plane(objects_json_file_path,objects_in_use):
    """ Generate Dictinary for Specified Object Plane

    Args:
        objects_json_file_path (string): path to json file
        with object plane specifications 

    Returns:
        dict: dictionary of all objects and their rotation
        limits
    """
    
    with open(objects_json_file_path) as json_file:
        objects_dict_original = json.load(json_file)
    
    objects_dict_for_object_plane = {}
    
    # generate duplicate objects specified by json file
    for obj in objects_dict_original:
        if objects_dict_original[obj]["max_number"] <= 0:
            pass
        
        else:   # objects_dict_original[obj]["max_number"] >= 1
            
            # assme this dictionary will not use the original object
            number_of_objects_to_duplicate = objects_dict_original[obj]["max_number"]   
            
            # check to see if item is already in use
            OBJECT_IN_USE = False
            if len(objects_in_use) > 0:
                for scene_obj_name in objects_in_use:
                    if scene_obj_name.split(".")[0] == obj: 
                        OBJECT_IN_USE = True
                        break
            
            if not OBJECT_IN_USE:  # add origional instance of object to dictionary

                # add the original to the object plane's dictionary
                objects_dict_for_object_plane[obj] = {}
                objects_dict_for_object_plane[obj]["rot_limits"] = objects_dict_original[obj]["rot_limits"]
                
                objects_in_use.append(obj)
                
                number_of_objects_to_duplicate -= 1
            
            
            # add duplicates to the object plane's dictionary
            for i in range(number_of_objects_to_duplicate):
                new_object_name = duplicate_object(obj)
                
                # add to dictionary (will eventually replace the list)
                objects_dict_for_object_plane[new_object_name] = {}
                objects_dict_for_object_plane[new_object_name]["rot_limits"] = objects_dict_original[obj]["rot_limits"]
                
                objects_in_use.append(new_object_name)
        
    return objects_dict_for_object_plane, objects_in_use

def placeCameraInVolumes(camera_volumes):
    """ Place the camera bpy.data.objects["Camera"] in one of multiple volumes

    Args:
        camera_volumes (list): All mesh volumes to be considred
    """
    
    # select camera volume probabilistically based on volume
    volume_sizes = np.zeros((len(camera_volumes)))
    for i,volume in enumerate(camera_volumes):
        volume_sizes[i] = np.array(bpy.data.objects[volume].dimensions).prod()

    volume_size_percentages = volume_sizes / volume_sizes.sum()
    camera_volume_selected = np.random.choice(np.arange(0,len(camera_volumes),1), 
                                                size=1, replace=True, p=volume_size_percentages)[0]
    placeCameraInVolume(camera_volumes[camera_volume_selected], roll=0)

def placeObjectsOnPlanes(object_plane_dictionaries):
    """ Place objects on multiple planes

    Args:
        object_plane_dictionaries (dict): Dictionary of objects for each plane
    """
    
    placed_object_footprints = []
    max_attemps_per_placement = 100
    for object_plane in object_plane_dictionaries:
        object_plane_dict = object_plane_dictionaries[object_plane]
        object_plane_dict_keys = list(object_plane_dict.keys())
        random.shuffle(object_plane_dict_keys)
        for obj_name in object_plane_dict_keys:
            placeObjectOnPlane(object_plane,obj_name, object_plane_dict,placed_object_footprints,max_attemps_per_placement)


def annotate_objects_in_image(segmentation_image, rgb_image, color_to_object_mapping,annotations_list,refs_list,image_id, image_name, tracking_variables, GENERATE_ANNOTATED_IMAGES):
    
    ann_id = tracking_variables["ann_id"]
    ref_id = tracking_variables["ref_id"]
    sent_id = tracking_variables["sent_id"]
    
    annotated_image = copy.deepcopy(rgb_image)
    
    max_number_of_annotations = segmentation_image.max()
    for IndexOB in range(max_number_of_annotations):
        IndexOB+=1
        if IndexOB in segmentation_image:
            mask = np.zeros_like(segmentation_image)
            mask[segmentation_image == IndexOB] = 255

            imgray2 = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(imgray2, 0,255, cv2.THRESH_BINARY)
            contours,hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            convex_contour = contours[0]
            
            number_of_contours = len(contours)
            
            if number_of_contours > 1:
                warnings.warn(f"{number_of_contours} cotours found with the same pass index. \
                    \n This suggests {number_of_contours-1} occlusions occured. \
                    \n Will proceed to group these partial contours as one contour as a contex hull.")
                
                # Find the convex hull object for all contours
                contours_appended = contours[0]
                for ctr in range(number_of_contours-1):
                    ctr += 1
                    contours_appended = np.vstack((contours_appended,contours[ctr]))
                                
                convex_contour = cv2.convexHull(contours_appended)
                        
            
            # area and segmentation coordinates
            area = cv2.contourArea(contours[0])
            segmentation_coords = contours[0].reshape(-1,2)
            for ctr_idx in range(len(contours)-1):
                area += cv2.contourArea(contours[ctr_idx])
                segmentation_coords = np.vstack((segmentation_coords,contours[ctr_idx].reshape(-1,2)))   
                
            # bounding box coordinates
            bbox_seg_coords = convex_contour.reshape(-1,2)
            bbox_coords = np.array([[bbox_seg_coords[:,0].min(),bbox_seg_coords[:,1].min()],
                                    [bbox_seg_coords[:,0].max(),bbox_seg_coords[:,1].max()]])
            
            # relative pose of object
            pose = relative_location("Camera",color_to_object_mapping[IndexOB])
            
            
            # provide information for instances.json
            anno_dict = {}
            anno_dict["segmentation"] = [segmentation_coords.reshape(-1).tolist()]
            anno_dict["area"] = area
            anno_dict["iscrowd"] = 0
            anno_dict["image_id"] = image_id
            anno_dict["bbox"] = bbox_coords.reshape(-1).tolist()
            anno_dict["category_id"] = lookup_category_id(color_to_object_mapping[IndexOB].split("_")[1])
            anno_dict["id"] = ann_id
            anno_dict["pose"] = pose.tolist()
            annotations_list.append(anno_dict)
            
            # provide information for refs.json
            refs_dict = {}
            refs_dict["sent_ids"] = []
            refs_dict["file_name"] = image_name
            refs_dict["ann_id"] = ann_id
            refs_dict["ref_id"] = ref_id
            refs_dict["image_id"] = image_id
            refs_dict["split"] = "train"            # all annotations are assumed training 
            refs_dict["sentences"] = []
            refs_dict["category_id"] = anno_dict["category_id"]
            refs_list.append(refs_dict)
                
            # update tracking variables
            ann_id += 1
            ref_id += 1
           
            if GENERATE_ANNOTATED_IMAGES:
                # draw green contour around object
                cv2.drawContours(annotated_image, contours, -1, (0,255,0), 2)
                
                # draw blue rectangle around object
                
                cv2.rectangle(annotated_image, (bbox_coords[0,0],bbox_coords[0,1]), 
                                            (bbox_coords[1,0],bbox_coords[1,1]), (255,0,0), 2) 
                
                # transparent box
                bottom_of_tag_y = bbox_coords[1,1]+15 if bbox_coords[1,1]+20 < annotated_image.shape[0] else annotated_image.shape[0]
                sub_img = annotated_image[bbox_coords[1,1]:bottom_of_tag_y, bbox_coords[0,0]:bbox_coords[0,0]+120]
                white_rect = np.ones(sub_img.shape, dtype=np.uint8) * 255
                res = cv2.addWeighted(sub_img, 0.5, white_rect, 0.5, 1.0)
                annotated_image[bbox_coords[1,1]:bottom_of_tag_y, bbox_coords[0,0]:bbox_coords[0,0]+120] = res
                
                # print relative xyz to camera
                text = str([round(pose[0],3),round(pose[1],3),round(pose[2],3)])
                cv2.putText(annotated_image, text, 
                            (int(bbox_coords[0,0]),int(bbox_coords[1,1]+ 10)), 
                            cv2.FONT_HERSHEY_SIMPLEX , 0.3, (0,0,255), 1, cv2.LINE_AA) 

    tracking_variables["ann_id"] = ann_id
    tracking_variables["ref_id"] = ref_id
    tracking_variables["sent_id"] = sent_id
    
    return annotations_list, refs_list, annotated_image, tracking_variables

def load_segmentation_image():
    """Load Segmentation Image Generated by Blender; name will
        be some variant of 'Segmentation####.png'

    Returns:
        bool: Was only one segmentation image found?
        np.array: Image of segmentation file if only one 
                    image was found
    """
    
    segmentation_file_location = os.getcwd() + '/data'
    segmentation_files_found = [filename for filename in os.listdir(segmentation_file_location) if filename.startswith("Segmentation")]

    # if multiple semgnetaiton files are found report error
    if (len(segmentation_files_found) > 1):
        warnings.warn(f"Multiple Segmentation Files Found in {segmentation_file_location} \
                        \nFiles: {segmentation_files_found}\
                        \nRemove one of these files to continue")
        return False, np.zeros((1))
    else:
        sementation_file_name = segmentation_files_found[0]
        segmentation_image = cv2.imread("data/" + sementation_file_name)
        
        # delete the segmentation image
        os.remove(segmentation_file_location + "/" + sementation_file_name)
        
        return True, segmentation_image

def lookup_category_id(category_name):
    f = open('categories.json')
    data = json.load(f)
    print(category_name)
    for a in data:
        if a["name"] == category_name:
            print(a["id"])
            return a["id"]
    
    warnings.warn(f"No category id was found for category name {category_name}")
    return ""

def generate_references():
    """
    input: take list with the following categoreis; annotation id | category id | centroid of image bbox | euclidian distance to camera
    ouptut: 0-N sentences if the annodation belows to an object that is on the extreme of the image (left, right, up, down) or extreme of the scene (front, back)
    """
    pass

TESTING = False

camera_volumes = []
### Define Camera Volumes #################################################


camera_volumes = ["CameraVolume1",
                "CameraVolume2",
                "CameraVolume3",
                "CameraVolume4",
                "CameraVolume5",]


###########################################################################
if TESTING: placeCameraInVolumes(camera_volumes)


# delete all duplicate objects and place all objects outside of envionrment
delete_all_duplicate_objects()
move_away_all_objects([5,5,0])

object_plane_dictionaries = {}
### Define Object Plane dictionaries here #################################

objects_in_use = []
object_plane_dictionaries["ObjectPlane1"],objects_in_use = dictionary_for_object_plane("object_plane_dictionaries/living_room_op1.json",objects_in_use)
object_plane_dictionaries["ObjectPlane2"],objects_in_use = dictionary_for_object_plane("object_plane_dictionaries/living_room_op2.json",objects_in_use)
object_plane_dictionaries["ObjectPlane3"],objects_in_use = dictionary_for_object_plane("object_plane_dictionaries/living_room_op3.json",objects_in_use)
object_plane_dictionaries["ObjectPlane4"],objects_in_use = dictionary_for_object_plane("object_plane_dictionaries/living_room_op3.json",objects_in_use)
object_plane_dictionaries["ObjectPlane5"],objects_in_use = dictionary_for_object_plane("object_plane_dictionaries/living_room_op3.json",objects_in_use)


###########################################################################
if TESTING: placeObjectsOnPlanes(object_plane_dictionaries)

if TESTING: 
    
    i = 0
    
    bpy.data.scenes["Scene"].cycles.samples = 5
    
    # set pass index for all objects to 0
    for obj in bpy.data.objects:
        bpy.data.objects[obj.name].pass_index = 0
    
    color_to_object_mapping = color_all_objects()

    # # render image
    # image_name = f"{str(i).zfill(6)}"
    # bpy.context.scene.render.filepath =  os.getcwd() + f"/data/images/{image_name}.png"
    # bpy.ops.render.render(write_still=True)
    
    
    # # annotate image
    # rgb_img = cv2.imread(bpy.context.scene.render.filepath) 
    
    # # load segmentaiton image
    # only_one_segmentation_image_found, segmentation_image = load_segmentation_image()
    # if only_one_segmentation_image_found: 

    #     # annotate objects
    #     annotate_objects_in_image(segmentation_image, rgb_img, color_to_object_mapping, image_name)
     



### Generate Dataset #########################    
GENERATE_DATASET = True
GENERATE_ANNOTATED_IMAGES = True

if GENERATE_DATASET:
    
    # create directory for images and json files
    current_time_stamp = str(datetime.now())
    dataset_path = os.getcwd()+f"/RefCOC0_3DS_{current_time_stamp}"
    os.mkdir(dataset_path)
    os.mkdir(dataset_path+"/images")
    os.mkdir(dataset_path+"/annotated")
    
    # initialize instances.json dictionary
    instances_dict = {}
    instances_dict["info"] = {
        "description": "This is dev 0.1 version of the 2024 RefCOCO 3D Synthetic Spatial dataset.",
        "version": "0.1",
        "year": 2024,
        "contributor": "University of Michigan",
        "date_created": f"{current_time_stamp}"
    }
    instances_dict["images"] = []
    instances_dict["annotations"] = []
    instances_dict["categories"] = {}
        
    # initialize refs.json list
    refs_list = []
    
    
    # dictionary of tracking variables
    tracking_variables = {}
    tracking_variables["ref_id"] = 0    # annotation id
    tracking_variables["ann_id"] = 0    # reference id
    tracking_variables["sent_id"] = 0   # sentence id
    
    
    # render settings
    bpy.data.scenes["Scene"].cycles.samples = 1
    num_enviornmetns = 1
    start_idx = 0
    renders_per_environment = 1
    start_time = time.time()

    total_render_count = num_enviornmetns * renders_per_environment
    
    
    renter_rates = np.zeros(total_render_count)
    print("\n\n\nSTARTING DATASET GENERATION...")
    for image_id in range(start_idx, start_idx + renders_per_environment):
        
        # randomly place camera in a volume defined by a cube mesh
        placeCameraInVolumes(camera_volumes)
        time.sleep(0.01)
        
        # Reset enviornment 
        move_away_all_objects([5,5,0])
        
        # randomly place objects on plane defined by a plane mesh
        placeObjectsOnPlanes(object_plane_dictionaries)
        
        # set pass index for all objects to 0
        for obj in bpy.data.objects:
            bpy.data.objects[obj.name].pass_index = 0
        
        color_to_object_mapping = color_all_objects()

        # render image
        image_name = str(image_id).zfill(6)
        bpy.context.scene.render.filepath =  dataset_path + f"/images/{image_name}.png"
        bpy.ops.render.render(write_still=True)
        
        
        # retrieve rgb and segmentation images
        rgb_img = cv2.imread(bpy.context.scene.render.filepath) 
        only_one_segmentation_image_found, segmentation_image = load_segmentation_image()
        if not only_one_segmentation_image_found: break
                
        
        # add info to instances_dict images
        images_dict = {}
        images_dict["file_name"] = f"{image_name}.png"
        images_dict["height"] = rgb_img.shape[0]
        images_dict["width"] = rgb_img.shape[1]
        images_dict["date_captured"] = current_time_stamp
        images_dict["id"] = image_id
        
        instances_dict["images"].append(images_dict)
        
        # add info to instances_dict annotations
        annotations_list = []
        annotations_list, refs_list, annotated_image, tracking_variables = annotate_objects_in_image(segmentation_image, 
                                                                                     rgb_img, 
                                                                                     color_to_object_mapping,
                                                                                     annotations_list,
                                                                                     refs_list,
                                                                                     image_id, 
                                                                                     image_name,
                                                                                     tracking_variables,
                                                                                     GENERATE_ANNOTATED_IMAGES)
        instances_dict["annotations"] += annotations_list
        
        cv2.imwrite(dataset_path + f"/annotated/{image_name}.png", annotated_image)
        
        
        # render rate statistics
        renter_rates[image_id] =  (time.time() - start_time) / (image_id + 1)
        seconds_remaining = renter_rates[image_id] * (total_render_count - image_id - 1)
        print(f'\nTotal Passed: {time.strftime("%H:%M:%S",time.gmtime(time.time()-start_time))} | Remaining Time: {time.strftime("%H:%M:%S",time.gmtime(seconds_remaining))}s')
        print(f'Current | Avg | Max | Min Renter Rates (s/img): {round(renter_rates[image_id],2)} | {round(renter_rates[:image_id+1].mean(),2)} | {round(renter_rates[:image_id+1].max(),2)} | {round(renter_rates[:image_id+1].min(),2)}')
        
        
        
    print("DATASET GENERATION COMPLETE!")


    with open(dataset_path+f"/instances.json", 'w') as f:
        json.dump(instances_dict, f)
        
    with open(dataset_path+f"/refs.json", 'w') as f:
        json.dump(refs_list, f)
    
        
