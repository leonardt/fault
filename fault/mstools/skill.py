import os
from pathlib import Path
from fault.subprocess_run import subprocess_run
from fault.user_cfg import FaultConfig


def run_skill(skill_cmds, cds_lib=None, cwd=None, disp_type='on_error',
              script=None, name=None):
    # set working directory if needed
    if cwd is None:
        cwd = FaultConfig.cwd
    cwd = Path(cwd).resolve()
    os.makedirs(cwd, exist_ok=True)

    # set cds.lib location if needed
    if cds_lib is None:
        cds_lib = FaultConfig.cds_lib
    cds_lib = Path(cds_lib).resolve()

    # set the name of the skill script if needed
    if name is None:
        if script is None:
            name = 'skill'
        else:
            name = Path(script).stem

    # determine where the script should be run
    run_dir = cds_lib.parent

    # write skill commands to file
    file_name = cwd / f'{name}.il'
    with open(file_name, 'w') as f:
        f.write(skill_cmds)
        f.flush()

    FaultConfig.print(f'Running SKILL script {file_name.name}', level=1)

    # run the skill commands
    args = []
    args += ['dbAccess']
    args += ['-load', str(Path(f.name).resolve())]
    subprocess_run(args, cwd=run_dir, err_str='*Error*', disp_type=disp_type,
                   script=script)
