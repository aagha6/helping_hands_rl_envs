import unittest
import time
import numpy as np
from tqdm import tqdm

import matplotlib.pyplot as plt

from helping_hands_rl_envs import env_factory

class TestBulletBumpyHouseBuilding4(unittest.TestCase):
  workspace = np.asarray([[0.3, 0.7],
                          [-0.2, 0.2],
                          [0, 0.50]])
  env_config = {'workspace': workspace, 'max_steps': 20, 'obs_size': 128, 'render': True, 'fast_mode': True,
                'seed': 0, 'action_sequence': 'pxyzrrr', 'num_objects': 6, 'random_orientation': True,
                'reward_type': 'sparse', 'simulate_grasp': True, 'perfect_grasp': False, 'robot': 'kuka',
                'workspace_check': 'point', 'physics_mode': 'fast', 'hard_reset_freq': 1000, 'object_scale_range': (0.6, 0.6),
                }

  planner_config = {'random_orientation': True, 'half_rotation': True}


  def testPlanner2(self):
    self.env_config['render'] = False
    num_processes = 20
    self.env_config['seed'] = 0
    env = env_factory.createEnvs(num_processes, 'pybullet', 'bumpy_house_building_4', self.env_config, self.planner_config)
    total = 0
    s = 0
    step_times = []
    env.reset()
    pbar = tqdm(total=500)
    while total < 500:
      t0 = time.time()
      action = env.getNextAction()
      t_plan = time.time() - t0

      (states_, in_hands_, obs_), rewards, dones = env.step(action, auto_reset=True)

      # (states_, in_hands_, obs_), rewards, dones = env.step(action, auto_reset=False)
      # if dones:
      #   env.reset()

      s += rewards.sum()
      total += dones.sum()
      t_action = time.time() - t0 - t_plan
      t = time.time() - t0
      step_times.append(t)

      pbar.set_description(
        '{}/{}, SR: {:.3f}, plan time: {:.2f}, action time: {:.2f}, avg step time: {:.2f}'
          .format(s, total, float(s) / total if total != 0 else 0, t_plan, t_action, np.mean(step_times))
      )
      pbar.update(dones.sum())
    env.close()

