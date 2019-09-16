import os
from pathlib import Path
from fault.subprocess_run import subprocess_run
from fault.spice_target import DeclareFromSpice
from fault import FaultConfig


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


def DeclareFromSchematic(lib, cell, *args, mode='digital', **kwargs):
    # generate the netlist
    out = si_netlist(lib, cell, *args, **kwargs)

    # create circuit from generated netlist
    circuit = DeclareFromSpice(out, subckt_name=f'{cell}', mode=mode)

    # return the circuit
    return circuit


def si_netlist(lib, cell, cds_lib=None, cwd=None, view='schematic',
               out=None, del_incl=True, env=None, add_to_env=None,
               disp_type='on_error'):
    # set defaults
    if cwd is None:
        cwd = FaultConfig.cwd
    if cds_lib is None:
        cds_lib = FaultConfig.cds_lib

    # path wrapping
    cwd = Path(cwd).resolve()

    # set output location
    if out is None:
        out = cwd / f'{cell}.sp'
    out = Path(out).resolve()

    # create the output directory if needed
    os.makedirs(cwd, exist_ok=True)

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
    subprocess_run(args, cwd=cwd, env=env, add_to_env=add_to_env,
                   disp_type=disp_type)

    # get netlist text and filter out include statements
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

    # return location where netlist was written
    return out
