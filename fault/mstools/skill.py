from pathlib import Path

from fault.subprocess_run import subprocess_run
from fault.user_cfg import FaultConfig


def run_skill(skill_cmds, cds_lib=None, cwd=None, name=None,
              disp_type='on_error', script=None):
    # set defaults
    if cwd is None:
        cwd = FaultConfig.cwd
    if cds_lib is None:
        cds_lib = FaultConfig.cds_lib
    if name is None:
        name = 'skill'

    # determine where the script should be run
    run_dir = Path(cds_lib).resolve().parent

    # write skill commands to file
    file_name = Path(cwd).resolve() / f'{name}.il'
    with open(file_name, 'w') as f:
        f.write(skill_cmds)
        f.flush()

    # run the skill commands
    args = []
    args += ['dbAccess']
    args += ['-load', str(Path(f.name).resolve())]
    subprocess_run(args, cwd=run_dir, err_str='*Error*', disp_type=disp_type,
                   script=script)
