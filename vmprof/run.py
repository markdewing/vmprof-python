from __future__ import print_function

import vmprof.tocallgrind

import argparse
import os.path
import shutil
import subprocess
import sys



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd",nargs=argparse.REMAINDER)
    parser.add_argument('-o', '--output', default=None, help="Output file (callgrind format)")
    args = parser.parse_args()
    if len(args.cmd) == 0:
        print("Usage: vmprofrun <python script> [arguments to script]")
        return


    vmprof_output_file = 'out.vmprof'

    cmd = [sys.executable, '-m', 'vmprof', '--output', vmprof_output_file]
    cmd.extend(args.cmd)

    p = subprocess.Popen(cmd)
    p.wait()
    print('pid:',p.pid)

    new_map_file = "perf-%d.map"%p.pid
    map_file = "/tmp/%s"%new_map_file
    is_numba = False
    if os.path.exists(map_file):
        shutil.move(map_file, new_map_file)
        # if map file exists, assume that we are running under Numba
        is_numba = True
    else:
        new_map_file = None

 
    new_vmprof_output_file  = "out-%d.vmprof"%p.pid
    if os.path.exists(vmprof_output_file):
        shutil.move(vmprof_output_file, new_vmprof_output_file)
    else:
        print("No vmprof output file")
        return

    if args.output:
        output_file = args.output
    else:
        output_file = "vmprof-%d.out"%p.pid

    vmprof.tocallgrind.output_callgrind(new_vmprof_output_file, new_map_file, output_file, remove_numba_dispatch=is_numba)


if __name__ == '__main__':
    main()
