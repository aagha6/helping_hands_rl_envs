import pybullet as pb
import numpy as np

from helping_hands_rl_envs.simulators import constants
from helping_hands_rl_envs.envs.pybullet_envs.close_loop_envs.close_loop_env import CloseLoopEnv
from helping_hands_rl_envs.simulators.pybullet.utils import transformations
from helping_hands_rl_envs.planners.close_loop_house_building_1_planner import CloseLoopHouseBuilding1Planner
from helping_hands_rl_envs.simulators.constants import NoValidPositionException

class CloseLoopHouseBuilding1Env(CloseLoopEnv):
  def __init__(self, config):
    super().__init__(config)
    assert self.num_obj >= 2

  def reset(self):
    while True:
      self.resetPybulletEnv()
      self.robot.moveTo([self.workspace[0].mean(), self.workspace[1].mean(), 0.2], transformations.quaternion_from_euler(0, 0, 0))
      try:
        self._generateShapes(constants.TRIANGLE, 1, random_orientation=self.random_orientation)
        self._generateShapes(constants.CUBE, self.num_obj-1, random_orientation=self.random_orientation)
      except NoValidPositionException as e:
        continue
      else:
        break
    return self._getObservation()

  def _getValidOrientation(self, random_orientation):
    if random_orientation:
      orientation = pb.getQuaternionFromEuler([0., 0., np.pi * (np.random.random_sample() - 0.5)])
    else:
      orientation = pb.getQuaternionFromEuler([0., 0., 0.])
    return orientation

  def _checkTermination(self):
    blocks = list(filter(lambda x: self.object_types[x] == constants.CUBE, self.objects))
    triangles = list(filter(lambda x: self.object_types[x] == constants.TRIANGLE, self.objects))
    return not self._isHolding() and self._checkStack(blocks + triangles) and self._checkObjUpright(triangles[0]) and self._isObjOnTop(triangles[0])

def createCloseLoopHouseBuilding1Env(config):
  return CloseLoopHouseBuilding1Env(config)

if __name__ == '__main__':
  import matplotlib.pyplot as plt
  workspace = np.asarray([[0.2, 0.8],
                          [-0.3, 0.3],
                          [0.01, 0.50]])
  env_config = {'workspace': workspace, 'max_steps': 100, 'obs_size': 128, 'render': True, 'fast_mode': True,
                'seed': 2, 'action_sequence': 'pxyzr', 'num_objects': 3, 'random_orientation': True,
                'reward_type': 'step_left', 'simulate_grasp': True, 'perfect_grasp': False, 'robot': 'kuka',
                'object_init_space_check': 'point', 'physics_mode': 'fast', 'object_scale_range': (1, 1), 'hard_reset_freq': 1000}
  planner_config = {'random_orientation': False, 'dpos': 0.05, 'drot': np.pi/8}
  env_config['seed'] = 1
  env = CloseLoopHouseBuilding1Env(env_config)
  planner = CloseLoopHouseBuilding1Planner(env, planner_config)
  s, in_hand, obs = env.reset()

  while True:
    action = planner.getNextAction()
    obs, reward, done = env.step(action)