import os
from pathlib import Path
import logging


class _FaultConfig:
    def __init__(self):
        # initialization
        self.remove_conda = False
        self.env_vars = {}
        self.path_env_vars = {}
        self.cds_lib = None
        self.lvs_rules = []
        self.xrc_rules = []

        # read in config information
        self.read_cfg_files()

        # determine simulation environment
        self.env = self.compute_env()

    def read_cfg_files(self):
        try:
            import yaml
        except ModuleNotFoundError:
            logging.warn('pyyaml not found, cannot parse config files.')
            logging.warn('Please run "pip install pyyaml" to fix this.')
            return

        locs = [Path.home() / '.faultrc', 'fault.yml', 'fault.yaml']
        for loc in locs:
            loc = Path(loc).resolve()
            if loc.exists():
                with open(loc, 'r') as f:
                    try:
                        opts = yaml.safe_load(f)
                        self.update_from_opts(opts=opts, loc=loc)
                    except yaml.YAMLError as yaml_err:
                        logging.warn(f'Skipping config file {loc} due to a parsing error.  Error message:')  # noqa
                        logging.warn(f'{yaml_err}')

    def update_from_opts(self, opts, loc):
        if 'remove_conda' in opts:
            self.remove_conda = opts['remove_conda']
        if 'add_env_vars' in opts:
            self.env_vars.update(opts['add_env_vars'])
        if 'env_vars' in opts:
            self.env_vars.update(opts['env_vars'])
        if 'path_env_vars' in opts:
            for key, val in opts['path_env_vars'].items():
                self.env_vars[key] = Path(loc.parent, val).resolve()
        if 'cds_lib' in opts:
            self.cds_lib = Path(loc.parent, opts['cds_lib']).resolve()
        if 'lvs_rules' in opts:
            self.lvs_rules.extend(opts['lvs_rules'])
        if 'xrc_rules' in opts:
            self.xrc_rules.extend(opts['xrc_rules'])

    def compute_env(self):
        env = os.environ.copy()

        if self.remove_conda:
            self.remove_conda_from_env(env)

        for key, val in self.env_vars.items():
            env[f'{key}'] = f'{val}'

        return env

    @staticmethod
    def remove_conda_from_env(env):
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


# Instantiate FaultConfig object to avoid having to parse the config
# files again and again
FaultConfig = _FaultConfig()
