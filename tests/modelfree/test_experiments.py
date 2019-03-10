"""Integration test: run experiments with some small & fast configs.

Only cursory 'smoke' checks -- there are plenty of errors this won't catch."""

import json
import os
from ray.tune.trial import Trial

import pytest

from modelfree.hyperparams import hyper_ex
from modelfree.score_agent import score_ex
from modelfree.policy_loader import AGENT_LOADERS
from modelfree.train_and_score import train_and_score
from modelfree.train import NO_VECENV, RL_ALGOS, train_ex


EXPERIMENTS = [score_ex, train_and_score, train_ex]


@pytest.mark.parametrize('experiment', EXPERIMENTS)
def test_experiment(experiment):
    """Smoke test to check the experiments runs with default config."""
    run = experiment.run()
    assert run.status == 'COMPLETED'


BASE_DIR = os.path.dirname(os.path.realpath(__file__))
SCORE_AGENT_CONFIGS = [
    {'agent_b_type': 'zoo', 'agent_b_path': '2', 'videos': True, 'episodes': 2},
    {'env_name': 'multicomp/KickAndDefend-v0', 'episodes': 1},
]
SCORE_AGENT_CONFIGS += [
    {
        'agent_b_type': rl_algo,
        'agent_b_path': os.path.join(BASE_DIR, 'dummy_sumo_ants', rl_algo),
        'episodes': 1,
    }
    for rl_algo in AGENT_LOADERS.keys() if rl_algo != 'zoo'
]


@pytest.mark.parametrize('config', SCORE_AGENT_CONFIGS)
def test_score_agent(config):
    """Smoke test for score agent to check it runs with some different configs."""
    config = dict(config)
    config['render'] = False  # faster without, test_experiment already tests with render

    run = score_ex.run(config_updates=config)
    assert run.status == 'COMPLETED'

    ties = run.result['ties']
    win_a, win_b = run.result['wincounts']
    assert sum([ties, win_a, win_b]) == run.config['episodes']


def load_json(fname):
    with open(fname) as f:
        return json.load(f)


TRAIN_CONFIGS = [
    {'num_env': 1},
    {'env_name': 'multicomp/KickAndDefend-v0'},
    {'normalize': False},
    {'victim_type': 'ppo2', 'victim_path': os.path.join(BASE_DIR, 'dummy_sumo_ants', 'ppo2')},
    {
        'env_name': 'multicomp/SumoHumans-v0',
        'rew_shape': True,
        'rew_shape_params': {'anneal_frac': 0.1},
    },
    {
        'env_name': 'multicomp/SumoHumans-v0',
        'victim_noise': True,
    }
]
TRAIN_CONFIGS += [{'rl_algo': algo, 'num_env': 1 if algo in NO_VECENV else 8}
                  for algo in RL_ALGOS.keys()]


@pytest.mark.parametrize('config', TRAIN_CONFIGS)
def test_train(config):
    config = dict(config)
    # Use a small number of steps to keep things quick
    config['batch_size'] = 512
    config['total_timesteps'] = 1024
    run = train_ex.run(config_updates=config)
    final_dir = run.result
    assert os.path.isdir(final_dir), "final result not saved"
    assert os.path.isfile(os.path.join(final_dir, 'model.pkl')), "model weights not saved"


def test_hyper():
    """Smoke test for hyperparameter search."""
    config = {
        'spec': {
            'resources_per_trial': {'cpu': 2},  # Travis only has 2 cores
        },
        'platform': 'pytest',  # prevent from uploading results
    }
    run = hyper_ex.run(config_updates=config)
    trials = run.result
    for trial in trials:
        assert isinstance(trial, Trial)
