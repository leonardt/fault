from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from fault.subprocess_run import subprocess_run


def run_skill(skill_cmds, cds_lib):
    cwd = Path(cds_lib).resolve().parent
    with NamedTemporaryFile(dir='.', suffix='.il', mode='w') as f:
        f.write(skill_cmds)
        f.flush()
        args = []
        args += ['dbAccess']
        args += ['-load', str(Path(f.name).resolve())]
        subprocess_run(args, cwd=cwd, err_str='*Error*')
