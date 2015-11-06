from __future__ import absolute_import, print_function

import click
import vmprof

# Dump profile stacks.  Useful for debugging.

def dump_stack(stack, libs, addrspace):
    for idx,entry in enumerate(stack):
        if isinstance(entry, int):
            addr = entry
        else:
            addr = entry.addr
        name, lib_addr, is_virtual, lib = addrspace.lookup(addr)
        print (hex(addr), name, lib)


def dump_stacks(prof_filename, do_raw=False, perf_file=''):
    extra_libs = []
    if perf_file:
        jit_lib = vmprof.reader.read_perf(perf_file)
        extra_libs = [jit_lib]

    lib_cache = dict()
    period, profiles, virtual_symbols, libs, interp_name, addrspace = vmprof.profiler.read_profile_raw(prof_filename, lib_cache, extra_libs=extra_libs)
    if not do_raw:
        profiles, _, _ = vmprof.profiler.process_stacks(profiles, addrspace, interp_name, virtual_only=False)

    print("Interpreter: %s  Period: %d\n"%(interp_name, period))
    idx = 0
    for sample in profiles:
        print("Sample %d, Thread id %s"%(idx, hex(sample[2])))
        stack = sample[0]
        dump_stack(stack, libs, addrspace)
        print("\n")
        idx += 1

  
@click.command()
@click.argument('profile', type=str)
@click.option('--raw', is_flag=True, help='No filtering of stacks')
@click.option('--perf', type=str, default='', help='Specify perf map file.')
def main(profile, raw, perf):
    dump_stacks(profile, do_raw=raw, perf_file=perf)

if __name__ == '__main__':
    main()

