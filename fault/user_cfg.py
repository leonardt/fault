import os
from pathlib import Path
import logging


class FaultConfig:
    def __init__(self):
        # initialize
        self.opts = {}

        # read in config information
        self.read_cfg_files()

    def read_cfg_files(self):
        try:
            import yaml
        except ModuleNotFoundError:
            logging.warning('pyyaml not found, cannot parse config files.')
            logging.warning('Please run "pip install pyyaml" to fix this.')
            return

        locs = [Path.home() / '.faultrc', Path('.') / 'fault.yml']
        for loc in locs:
            if loc.exists():
                with open(loc, 'r') as f:
                    try:
                        new_opts = yaml.safe_load(f)
                        self.opts.update(new_opts)
                    except yaml.YAMLError as yaml_err:
                        logging.warning(f'Skipping config file {loc} due to a parsing error.  Error message:')  # noqa
                        logging.warning(f'{yaml_err}')

    def get_sim_env(self):
        env = os.environ.copy()

        if self.opts.get('remove_conda', False):
            self.remove_conda(env)

        for key, val in self.opts.get('add_env_vars', {}).items():
            env[f'{key}'] = f'{val}'

        return env

    @staticmethod
    def remove_conda(env):
        '''Returns a copy of the current environment with conda directories
           removed from the path.'''

        # find the location of the conda installation
        # if the variable is not found, then just
        # return the original environment
        try:
            conda_prefix = env['CONDA_PREFIX']
        except KeyError:
            return env

        # convert to Path object
        conda_prefix = os.path.realpath(os.path.expanduser(conda_prefix))
        conda_prefix = Path(conda_prefix)

        # split up the path into individual entries, then filter out
        # those starting with the CONDA_PREFIX
        path_entries = env['PATH'].split(os.pathsep)
        path_entries = [Path(entry) for entry in path_entries]
        path_entries = [entry for entry in path_entries
                        if conda_prefix not in entry.parents]

        # update the PATH variable
        env['PATH'] = os.pathsep.join(str(entry) for entry in path_entries)
