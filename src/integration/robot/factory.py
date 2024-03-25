#!/usr/bin/env python3

from enum import Enum
from grippers import GripperNode
from base import BaseNode
from ur5e_arm import UR5e_Arm
from dexterity import Dexterity

class GenericComponentMetaData():
    def __init__(self, name, component, args):
        self.name = name
        self.component = component
        self.args = args

class ComponentId(Enum):
    BASE            = 0
    LEFT_ARM        = 1
    RIGHT_ARM       = 2
    LEFT_GRIPPER    = 3
    RIGHT_GRIPPER   = 4

def convert_int_to_id(key):
    for e in ComponentId:
        if e.value == key:
            return e

def ComponentFactory():
    return  {
                ComponentId.BASE          : GenericComponentMetaData("Base", BaseNode, {}),
                ComponentId.LEFT_GRIPPER  : GenericComponentMetaData("Left_Gripper", GripperNode, {"dexterity":Dexterity.LEFT}),
                ComponentId.RIGHT_GRIPPER : GenericComponentMetaData("Right_Gripper", GripperNode, {"dexterity":Dexterity.RIGHT}),
            }
