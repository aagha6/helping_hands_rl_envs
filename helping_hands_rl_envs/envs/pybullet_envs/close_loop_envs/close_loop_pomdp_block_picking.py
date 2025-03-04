import pybullet as pb
import numpy as np

from helping_hands_rl_envs.simulators import constants
from helping_hands_rl_envs.envs.pybullet_envs.close_loop_envs.close_loop_env import CloseLoopEnv
from helping_hands_rl_envs.simulators.pybullet.utils import transformations
from helping_hands_rl_envs.planners.close_loop_pomdp_block_picking_planner import CloseLoopPomdpBlockPickingPlanner

class CloseLoopPomdpBlockPickingEnv(CloseLoopEnv):
  def __init__(self, config):
    super().__init__(config)

  def reset(self, target_obj_idx, noise=False):
    self.target_obj_idx = target_obj_idx
    self.resetPybulletEnv()
    self.robot.moveTo([self.workspace[0].mean(), self.workspace[1].mean(), 0.2], transformations.quaternion_from_euler(0, 0, 0))
    self.robot.openGripper()

    if noise:
      [noise_x1, noise_y1, noise_x2, noise_y2] = np.random.uniform(-0.01, 0.01, 4)
      [noise_yaw_1, noise_yaw_2] = np.random.uniform(-0.15, 0.15, 2)
    else:
      noise_x1 = noise_x2 = noise_y1 = noise_y2 = 0
      noise_yaw_1 = noise_yaw_2 = 0

    # rot_1 = [transformations.quaternion_from_euler(0.0, 0.0, noise_yaw_1)]
    # rot_2 = [transformations.quaternion_from_euler(0.0, 0.0, noise_yaw_2)]

    if target_obj_idx == 0:
      self._generateShapes(constants.CUBE, 1, cube_color='red', random_orientation=self.random_orientation)
      self._generateShapes(constants.CUBE, 1, cube_color='blue', random_orientation=self.random_orientation)
    elif (target_obj_idx == 1):
      self._generateShapes(constants.CUBE, 1, cube_color='blue', random_orientation=self.random_orientation)
      self._generateShapes(constants.CUBE, 1, cube_color='red', random_orientation=self.random_orientation)

    return self._getObservation()

  def _getValidOrientation(self, random_orientation):
    if random_orientation:
      orientation = pb.getQuaternionFromEuler([0., 0., np.pi/2 * (np.random.random_sample() - 0.5)])
    else:
      orientation = pb.getQuaternionFromEuler([0., 0., 0.])
    return orientation

  def _checkTermination(self):
    gripper_z = self.robot._getEndEffectorPosition()[-1]
    return self.robot.holding_obj == self.objects[self.target_obj_idx] and gripper_z > 0.08

def createCloseLoopPomdpBlockPickingEnv(config):
  return CloseLoopPomdpBlockPickingEnv(config)

if __name__ == '__main__':
  import matplotlib.pyplot as plt
  workspace = np.asarray([[0.2, 0.8],
                          [-0.3, 0.3],
                          [0.01, 0.50]])
  env_config = {'workspace': workspace, 'max_steps': 100, 'obs_size': 128, 'render': True, 'fast_mode': True,
                'seed': 2, 'action_sequence': 'pxyzr', 'num_objects': 1, 'random_orientation': False,
                'reward_type': 'step_left', 'simulate_grasp': True, 'perfect_grasp': False, 'robot': 'kuka',
                'object_init_space_check': 'point', 'physics_mode': 'fast', 'object_scale_range': (1, 1), 'hard_reset_freq': 1000}
  planner_config = {'random_orientation': False, 'dpos': 0.05, 'drot': np.pi/8}
  env_config['seed'] = 1
  env = CloseLoopPomdpBlockPickingEnv(env_config)
  planner = CloseLoopPomdpBlockPickingPlanner(env, planner_config)
  s, in_hand, obs = env.reset(0)
  # while True:
  #   current_pos = env.robot._getEndEffectorPosition()
  #   current_rot = transformations.euler_from_quaternion(env.robot._getEndEffectorRotation())
  #
  #   block_pos = env.objects[0].getPosition()
  #   block_rot = transformations.euler_from_quaternion(env.objects[0].getRotation())
  #
  #   pos_diff = block_pos - current_pos
  #   rot_diff = np.array(block_rot) - current_rot
  #   pos_diff[pos_diff // 0.01 > 1] = 0.01
  #   pos_diff[pos_diff // -0.01 > 1] = -0.01
  #
  #   rot_diff[rot_diff // (np.pi/32) > 1] = np.pi/32
  #   rot_diff[rot_diff // (-np.pi/32) > 1] = -np.pi/32
  #
  #   action = [1, pos_diff[0], pos_diff[1], pos_diff[2], rot_diff[2]]
  #   obs, reward, done = env.step(action)

  while True:
    action = planner.getNextAction(0)
    obs, reward, done = env.step(action)
    if done:
      break

  # fig, axs = plt.subplots(8, 5, figsize=(25, 40))
  # for i in range(40):
  #   action = planner.getNextAction()
  #   obs, reward, done = env.step(action)
  #   axs[i//5, i%5].imshow(obs[2][0], vmax=0.3)
  # env.reset()
  # fig.show()