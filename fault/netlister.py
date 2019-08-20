from pathlib import Path
from fault.subprocess_run import subprocess_run


si_env_tmpl = '''\
simLibName = "{lib}"
simCellName = "{cell}"
simViewName = "{view}"
simSimulator = "auCdl"
simNotIncremental = 't
simReNetlistAll = nil
simViewList = '("auCdl" "schematic")
simStopList = '("auCdl")
hnlNetlistFileName = "netlist"
resistorModel = ""
shortRES = 2000.0
preserveRES = 't
checkRESVAL = 't
checkRESSIZE = 'nil
preserveCAP = 't
checkCAPVAL = 't
checkCAPAREA = 'nil
preserveDIO = 't
checkDIOAREA = 't
checkDIOPERI = 't
checkCAPPERI = 'nil
simPrintInhConnAttributes = 'nil
checkScale = "meter"
checkLDD = 'nil
pinMAP = 'nil
preserveBangInNetlist = 'nil
shrinkFACTOR = 0.0
globalPowerSig = ""
globalGndSig = ""
displayPININFO = 't
preserveALL = 't
setEQUIV = ""
incFILE = ""
auCdlDefNetlistProc = "ansCdlSubcktCall"
'''


def si_netlist(lib, cell, cds_lib='cds.lib', cwd='.', view='schematic',
               out='netlist', del_incl=True, env=None):
    # path wrapping
    cwd = Path(cwd)
    out = Path(out)

    # write si.env file
    si_env = si_env_tmpl.format(lib=lib, cell=cell, view=view)
    with open(cwd / 'si.env', 'w') as f:
        f.write(si_env)

    # run netlister
    args = []
    args += ['si']
    args += ['-cdslib', f'{cds_lib}']
    args += ['-batch']
    args += ['-command', 'netlist']
    subprocess_run(args, cwd=cwd, env=env)

    # get netlist text and filter out include statementw
    with open(cwd / 'netlist', 'r') as f:
        lines = f.readlines()
    text = ''
    for line in lines:
        line_lower = line.strip().lower()
        if del_incl and line_lower.startswith('.include'):
            continue
        else:
            text += line

    # write netlist to desired file
    with open(out, 'w') as f:
        f.write(text)
