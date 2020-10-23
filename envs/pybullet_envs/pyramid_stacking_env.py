import numpy as np

from helping_hands_rl_envs.envs.pybullet_envs.pybullet_env import PyBulletEnv
from helping_hands_rl_envs.simulators import constants

class PyramidStackingEnv(PyBulletEnv):
  ''''''
  def __init__(self, config):
    super(PyramidStackingEnv, self).__init__(config)

  def step(self, action):
    self.takeAction(action)
    self.wait(100)
    obs = self._getObservation(action)
    done = self._checkTermination()
    reward = 1.0 if done else 0.0

    if not done:
      done = self.current_episode_steps >= self.max_steps or not self.isSimValid()
    self.current_episode_steps += 1

    return obs, reward, done

  def reset(self):
    ''''''
    super(PyramidStackingEnv, self).reset()
    self._generateShapes(constants.CUBE, self.num_obj, random_orientation=self.random_orientation)
    return self._getObservation()

  def _checkTermination(self):
    ''''''
    obj_z = [obj.getZPosition() for obj in self.objects]
    if np.allclose(obj_z[0], obj_z):
      return False

    top_obj = self.objects[np.argmax(obj_z)]
    mask = np.array([True] * self.num_obj)
    mask[np.argmax(obj_z)] = False
    bottom_objs = np.array(self.objects)[mask]
    return self._checkInBetween(top_obj, bottom_objs[0], bottom_objs[1], threshold=0.01) and \
           self._checkAdjacent(bottom_objs[0], bottom_objs[1])

def createPyramidStackingEnv(config):
  return PyramidStackingEnv(config)
