import pybullet as pb
import numpy as np
import skimage.transform as sk_transform
from helping_hands_rl_envs.envs.pybullet_envs.pybullet_env import PyBulletEnv
from helping_hands_rl_envs.simulators import constants
from helping_hands_rl_envs.simulators.pybullet.utils import transformations
from helping_hands_rl_envs.simulators.pybullet.utils.renderer import Renderer
from helping_hands_rl_envs.simulators.pybullet.utils.ortho_sensor import OrthographicSensor
from helping_hands_rl_envs.simulators.pybullet.utils import pybullet_util
import helping_hands_rl_envs.envs.pybullet_envs.constants as py_constants


class CloseLoopEnv(PyBulletEnv):
  def __init__(self, config):
    super().__init__(config)
    if 'view_type' not in config:
      config['view_type'] = 'camera_center_xyzr'
    if 'obs_type' not in config:
      config['obs_type'] = 'pixel'
    self.view_type = config['view_type']
    self.obs_type = config['obs_type']
    assert self.view_type in ['render_center', 'render_fix', 'camera_center_xyzr', 'camera_center_xyr',
                              'camera_center_xyz', 'camera_center_xy', 'camera_fix',
                              'camera_center_xyr_height', 'camera_center_xyz_height', 'camera_center_xy_height',
                              'camera_fix_height']

    self.robot.home_positions = [-0.4446, 0.0837, -2.6123, 1.8883, -0.0457, -1.1810, 0.0699, 0., 0., 0., 0., 0., 0., 0., 0.]
    self.robot.home_positions_joint = self.robot.home_positions[:7]

    self.ws_size = max(self.workspace[0][1] - self.workspace[0][0], self.workspace[1][1] - self.workspace[1][0])
    if self.view_type.find('center') > -1:
      self.ws_size *= 1.5

    cam_pos = [self.workspace[0].mean(), self.workspace[1].mean(), 0.29]
    target_pos = [self.workspace[0].mean(), self.workspace[1].mean(), 0]
    cam_up_vector = [-1, 0, 0]
    self.sensor = OrthographicSensor(cam_pos, cam_up_vector, target_pos, self.ws_size, 0.1, 1)
    self.sensor.setCamMatrix(cam_pos, cam_up_vector, target_pos)
    self.renderer = Renderer(self.workspace)

  def _getValidOrientation(self, random_orientation):
    if random_orientation:
      orientation = pb.getQuaternionFromEuler([0., 0., np.pi * (np.random.random_sample() - 0.5)])
    else:
      orientation = pb.getQuaternionFromEuler([0., 0., 0.])
    return orientation

  def step(self, action):
    p, x, y, z, rot = self._decodeAction(action)
    current_pos = self.robot._getEndEffectorPosition()
    current_rot = transformations.euler_from_quaternion(self.robot._getEndEffectorRotation())

    # bTg = transformations.euler_matrix(0, 0, current_rot[-1])
    # bTg[:3, 3] = current_pos
    # gTt = np.eye(4)
    # gTt[:3, 3] = [x, y, z]
    # bTt = bTg.dot(gTt)
    # pos = bTt[:3, 3]

    pos = np.array(current_pos) + np.array([x, y, z])
    rot = np.array(current_rot) + np.array(rot)
    rot_q = pb.getQuaternionFromEuler(rot)
    pos[0] = np.clip(pos[0], self.workspace[0, 0], self.workspace[0, 1])
    pos[1] = np.clip(pos[1], self.workspace[1, 0], self.workspace[1, 1])
    pos[2] = np.clip(pos[2], self.workspace[2, 0], self.workspace[2, 1])
    self.robot.moveTo(pos, rot_q, dynamic=True)
    self.robot.controlGripper(p)
    self.robot.adjustGripperCommand()
    self.setRobotHoldingObj()
    obs = self._getObservation(action)
    valid = self.isSimValid()
    if valid:
      done = self._checkTermination()
      reward = 1.0 if done else 0.0
    else:
      done = True
      reward = 0
    if not done:
      done = self.current_episode_steps >= self.max_steps
    self.current_episode_steps += 1

    return obs, reward, done

  def setRobotHoldingObj(self):
    self.robot.holding_obj = self.robot.getPickedObj(self.objects)

  def setRobotHoldingObjWithRotConstraint(self):
    self.robot.holding_obj = None
    for obj in self.objects:
      obj_rot = transformations.euler_from_quaternion(obj.getRotation())[-1]
      gripper_rot = transformations.euler_from_quaternion(self.robot._getEndEffectorRotation())[-1]
      angle_diff = abs(gripper_rot - obj_rot)
      angle_diff = min(angle_diff, abs(angle_diff - np.pi))
      angle_diff = min(angle_diff, abs(angle_diff - np.pi / 2))
      if len(pb.getContactPoints(self.robot.id, obj.object_id)) >= 2 and angle_diff < np.pi / 12:
        self.robot.holding_obj = obj
        break

  def _scaleX(self, x):
    scaled = 2 * (x - self.workspace[0, 0]) / (self.workspace[0, 1] - self.workspace[0, 0]) - 1
    return np.clip(scaled, -1, 1)

  def _scaleY(self, y):
    scaled = 2 * (y - self.workspace[1, 0]) / (self.workspace[1, 1] - self.workspace[1, 0]) - 1
    return np.clip(scaled, -1, 1)

  def _scaleZ(self, z):
    scaled = 2 * (z - self.workspace[2, 0]) / (self.workspace[2, 1] - self.workspace[2, 0]) - 1
    return np.clip(scaled, -1, 1)

  def _scaleRz(self, rz):
    while rz < -np.pi:
      rz += 2*np.pi
    while rz > np.pi:
      rz -= 2*np.pi
    scaled = 2 * (rz - -np.pi) / (2*np.pi) - 1
    return np.clip(scaled, -1, 1)

  def _scalePos(self, pos):
    return np.array([self._scaleX(pos[0]), self._scaleY(pos[1]), self._scaleZ(pos[2])])

  def getObjectPoses(self, objects=None):
    if objects is None: objects = self.objects

    obj_poses = list()
    for obj in objects:
      pos, rot = obj.getPose()
      rot = self.convertQuaternionToEuler(rot)

      obj_poses.append(pos + rot)
    return np.array(obj_poses)

  def _getVecObservation(self):
    '''
    get the observation in vector form. The observation has a size of (1+4+4*n), where the first value is the gripper
    state, the following 4-vector is the gripper's (x, y, z, rz), and the n 4-vectors afterwards are the (x, y, z, rz)s
    of the objects in the scene
    :return: the observation vector in np.array
    '''
    gripper_pos = self.robot._getEndEffectorPosition()
    scaled_gripper_pos = self._scalePos(gripper_pos)
    gripper_rz = transformations.euler_from_quaternion(self.robot._getEndEffectorRotation())[2]
    scaled_gripper_rz = self._scaleRz(gripper_rz)
    obj_poses = self.getObjectPoses()
    obj_poses = np.stack((obj_poses[:, 0], obj_poses[:, 1], obj_poses[:, 2], obj_poses[:, 5]), 1)
    scaled_obj_poses = []
    for i in range(obj_poses.shape[0]):
      scaled_obj_poses.append(
        np.concatenate([self._scalePos(obj_poses[i, :3]), np.array([self._scaleRz(obj_poses[i, 3])])]))
    scaled_obj_poses = np.concatenate(scaled_obj_poses)
    gripper_state = self.robot.getGripperOpenRatio()
    gripper_state = gripper_state * 2 - 1
    gripper_state = np.clip(gripper_state, -1, 1)
    # gripper_state = 1 if self._isHolding() else -1
    obs = np.concatenate(
      [np.array([gripper_state]), scaled_gripper_pos, np.array([scaled_gripper_rz]), scaled_obj_poses])
    return obs

  def _getObservation(self, action=None):
    ''''''
    if self.obs_type is 'pixel':
      self.heightmap = self._getHeightmap()
      return self._isHolding(), None, self.heightmap.reshape([1, self.heightmap_size, self.heightmap_size])
    else:
      obs = self._getVecObservation()
      return self._isHolding(), None, obs

  def _getHeightmap(self):
    gripper_pos = self.robot._getEndEffectorPosition()
    gripper_rz = transformations.euler_from_quaternion(self.robot._getEndEffectorRotation())[2]
    if self.view_type == 'render_center':
      self.renderer.getNewPointCloud()
      return self.renderer.getTopDownDepth(self.workspace_size * 1.5, self.heightmap_size, gripper_pos, gripper_rz)
    elif self.view_type == 'render_fix':
      return self.renderer.getTopDownHeightmap(self.heightmap_size)

    elif self.view_type == 'camera_center_xyzr':
      # xyz centered, alighed
      gripper_pos[2] += 0.12
      target_pos = [gripper_pos[0], gripper_pos[1], 0]
      T = transformations.euler_matrix(0, 0, gripper_rz)
      cam_up_vector = T.dot(np.array([-1, 0, 0, 1]))[:3]
      self.sensor.setCamMatrix(gripper_pos, cam_up_vector, target_pos)
      heightmap = self.sensor.getHeightmap(self.heightmap_size)
      depth = -heightmap + gripper_pos[2]
      return depth
    elif self.view_type in ['camera_center_xyr', 'camera_center_xyr_height']:
      # xy centered, aligned
      target_pos = [gripper_pos[0], gripper_pos[1], 0]
      T = transformations.euler_matrix(0, 0, gripper_rz)
      cam_up_vector = T.dot(np.array([-1, 0, 0, 1]))[:3]
      cam_pos = [gripper_pos[0], gripper_pos[1], 0.29]
      self.sensor.setCamMatrix(cam_pos, cam_up_vector, target_pos)
      heightmap = self.sensor.getHeightmap(self.heightmap_size)
      if self.view_type == 'camera_center_xyr':
        depth = -heightmap + gripper_pos[2]
      else:
        depth = heightmap
      return depth
    elif self.view_type in ['camera_center_xyz', 'camera_center_xyz_height']:
      # xyz centered, gripper will be visible
      gripper_pos[2] += 0.12
      target_pos = [gripper_pos[0], gripper_pos[1], 0]
      cam_up_vector = [-1, 0, 0]
      self.sensor.setCamMatrix(gripper_pos, cam_up_vector, target_pos)
      heightmap = self.sensor.getHeightmap(self.heightmap_size)
      if self.view_type == 'camera_center_xyz':
        depth = -heightmap + gripper_pos[2]
      else:
        depth = heightmap
      return depth
    elif self.view_type in ['camera_center_xy', 'camera_center_xy_height']:
      # xy centered
      target_pos = [gripper_pos[0], gripper_pos[1], 0]
      cam_up_vector = [-1, 0, 0]
      cam_pos = [gripper_pos[0], gripper_pos[1], 0.29]
      self.sensor.setCamMatrix(cam_pos, cam_up_vector, target_pos)
      heightmap = self.sensor.getHeightmap(self.heightmap_size)
      if self.view_type == 'camera_center_xy':
        depth = -heightmap + gripper_pos[2]
      else:
        depth = heightmap
      return depth
    elif self.view_type in ['camera_fix', 'camera_fix_height']:
      heightmap = self.sensor.getHeightmap(self.heightmap_size)
      if self.view_type == 'camera_fix':
        depth = -heightmap + gripper_pos[2]
      else:
        depth = heightmap
      return depth
    else:
      raise NotImplementedError

  def _encodeAction(self, primitive, x, y, z, r):
    if hasattr(r, '__len__'):
      assert len(r) in [1, 2, 3]
      if len(r) == 1:
        rz = r[0]
        ry = 0
        rx = 0
      elif len(r) == 2:
        rz = r[0]
        ry = 0
        rx = r[1]
      else:
        rz = r[0]
        ry = r[1]
        rx = r[2]
    else:
      rz = r
      ry = 0
      rx = 0

    primitive_idx, x_idx, y_idx, z_idx, rot_idx = map(lambda a: self.action_sequence.find(a),
                                                      ['p', 'x', 'y', 'z', 'r'])
    action = np.zeros(len(self.action_sequence), dtype=float)
    if primitive_idx != -1:
      action[primitive_idx] = primitive
    if x_idx != -1:
      action[x_idx] = x
    if y_idx != -1:
      action[y_idx] = y
    if z_idx != -1:
      action[z_idx] = z
    if rot_idx != -1:
      if self.action_sequence.count('r') == 1:
        action[rot_idx] = rz
      elif self.action_sequence.count('r') == 2:
        action[rot_idx] = rz
        action[rot_idx+1] = rx
      elif self.action_sequence.count('r') == 3:
        action[rot_idx] = rz
        action[rot_idx+1] = ry
        action[rot_idx+2] = rx

    return action

  # def isSimValid(self):
  #   all_upright = np.all(list(map(lambda o: self._checkObjUpright(o, threshold=np.deg2rad(10)), self.objects)))
  #   return all_upright and super().isSimValid()

  def _checkStack(self, objects=None):
    # 2-step checking
    if super()._checkStack(objects):
      self.wait(100)
      return super()._checkStack(objects)
    return False

if __name__ == '__main__':
  import matplotlib.pyplot as plt
  workspace = np.asarray([[0.2, 0.8],
                          [-0.3, 0.3],
                          [0, 0.25]])
  env_config = {'workspace': workspace, 'max_steps': 10, 'obs_size': 128, 'render': True, 'fast_mode': True,
                'seed': 2, 'action_sequence': 'pxyzr', 'num_objects': 6, 'random_orientation': False,
                'reward_type': 'step_left', 'simulate_grasp': True, 'perfect_grasp': False, 'robot': 'kuka',
                'object_init_space_check': 'point', 'physics_mode': 'fast', 'object_scale_range': (1, 1)}
  planner_config = {'random_orientation': True}
  env = CloseLoopEnv(env_config)
  s, obs = env.reset()

  fig, axs = plt.subplots(4, 5, figsize=(25, 20))
  for i in range(20):
    action = [-1, 0, 0, -0.01, 0]
    obs, reward, done = env.step(action)
    axs[i//5, i%5].imshow(obs[1][0], vmax=0.3)
  fig.show()

  while True:
    action = [-1, 0, 0, -0.01, 0]
    obs, reward, done = env.step(action)
    plt.imshow(obs[2][0], vmax=0.3)
    plt.colorbar()
    plt.show()

