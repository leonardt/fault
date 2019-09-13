import os
from pathlib import Path
import logging


class _FaultConfig:
    def __init__(self):
        # initialization
        self.remove_conda = False
        self.cwd = 'build/'
        self.env_vars = {}
        self.path_env_vars = {}
        self.cds_lib = None
        self.cal_lvs_rules = []
        self.cal_xrc_rules = []
        self.ngspice_models = []
        self.hspice_models = []
        self.spectre_models = []

        # read in config information
        self.read_cfg_files()

        # determine simulation environment
        self.env = self.compute_env()

    def read_cfg_files(self):
        locs = [Path.home() / '.faultrc',
                'fault.yml',
                'fault.yaml']
        for loc in locs:
            self.load_yaml(loc)

    def load_yaml(self, loc):
        try:
            import yaml
        except ModuleNotFoundError:
            logging.warn('pyyaml not found, cannot parse config files.')
            logging.warn('Please run "pip install pyyaml" to fix this.')
            return

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
        for opt_name, opt_val in opts.items():
            if opt_name == 'remove_conda':
                self.remove_conda = opt_val
            elif opt_name in ['env_vars', 'add_env_vars']:
                self.env_vars.update(opt_val)
            elif opt_name == 'path_env_vars':
                for key, val in opt_val.items():
                    self.env_vars[key] = Path(loc.parent, val).resolve()
            elif opt_name == 'cds_lib':
                self.cds_lib = Path(loc.parent, opt_val).resolve()
            elif opt_name == 'cal_lvs_rules':
                for val in opt_val:
                    self.cal_lvs_rules.append(Path(loc.parent, val).resolve())
            elif opt_name == 'cal_xrc_rules':
                for val in opt_val:
                    self.cal_xrc_rules.append(Path(loc.parent, val).resolve())
            elif opt_name == 'ngspice_models':
                for val in opt_val:
                    self.ngspice_models.append(Path(loc.parent, val).resolve())
            elif opt_name == 'hspice_models':
                for val in opt_val:
                    self.hspice_models.append(Path(loc.parent, val).resolve())
            elif opt_name == 'spectre_models':
                for val in opt_val:
                    self.spectre_models.append(Path(loc.parent, val).resolve())
            elif opt_name == 'include':
                if not isinstance(opt_val, list):
                    opt_val = [opt_val]
                for val in opt_val:
                    self.load_yaml(Path(loc.parent, val))

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
