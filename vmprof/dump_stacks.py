from __future__ import absolute_import

import click
import vmprof

def dump_stack(stack, virtual_ips, libs, addrspace, jit_sym):
    for idx,entry in enumerate(stack):
        name, addr, is_virtual, lib = addrspace.lookup(entry)
        if not lib and idx != len(stack)-1:
            if jit_sym:
                name, offset = find_jit_sym(jit_sym, addr)
                if name:
                    print 'JIT: (offset = %s)'%hex(offset),
            else:
                print 'MISSING SYM:',
        print hex(entry),name, is_virtual, lib

def find_jit_sym(jit_sym, addr):
    for start, size, name in jit_sym:
        if addr >= start and addr <= start+size:
            offset = addr - start
            return name, offset
    return None, 0


def dump_stacks(prof_filename, perf_filename):
    period, profiles, virtual_symbols, libs, interp_name, addrspace, jit_sym = \
        vmprof.read_profile_bare(prof_filename, perf_filename=perf_filename)

    idx = 0
    for sample in profiles:
        print("Sample %d"%idx)
        dump_stack(sample[0], virtual_symbols, libs, addrspace, jit_sym)
        print("\n")
        idx += 1


@click.command()
@click.argument('profile', type=str)
@click.option('--perf', type=str, default='', help='Perf map file')
def main(profile, perf):
    dump_stacks(profile, perf)
    


if __name__ == '__main__':
    main()
