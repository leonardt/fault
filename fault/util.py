import os
import os.path
from pathlib import Path


def flatten(l):
    return [item for sublist in l for item in sublist]


def remove_conda(env):
    '''Returns a copy of the current environment with conda directories
       removed from the path.'''

    # copy the environment
    env = os.environ.copy()

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

    return env
