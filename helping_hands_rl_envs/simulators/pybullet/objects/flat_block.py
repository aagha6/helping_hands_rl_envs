import sys
sys.path.append('..')

import pybullet as pb
import numpy as np
import os

import helping_hands_rl_envs
from helping_hands_rl_envs.simulators.pybullet.objects.pybullet_object import PybulletObject
from helping_hands_rl_envs.simulators import constants
from helping_hands_rl_envs.simulators.pybullet.utils import transformations

class FlatBlock(PybulletObject):
  def __init__(self, pos, rot, scale, color='red'):
    if color == 'red':
      color_code = [0, 0, 1, 1]
      mass = 0.5
    else:
      color_code = [0, 0, 1, 1]
      mass = 0.0
    bottom_visual = pb.createVisualShape(pb.GEOM_BOX, halfExtents=[0.05*scale, 0.05*scale, 0.025], rgbaColor=[1, 1, 1, 1])

    # if color == 'blue':
    #   bottom_collision = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=[0.0*scale, 0.0*scale, 0.0])
    # else:
    bottom_collision = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=[0.05*scale, 0.05*scale, 0.025])
    object_id = pb.createMultiBody(baseMass=mass,
                            baseCollisionShapeIndex=bottom_collision,
                            baseVisualShapeIndex=bottom_visual,
                            basePosition=pos,
                            baseOrientation=rot,
                            )
    pb.changeVisualShape(object_id, -1, rgbaColor=color_code)
    super(FlatBlock, self).__init__(constants.FLAT_BLOCK, object_id)