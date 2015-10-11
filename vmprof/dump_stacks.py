from __future__ import absolute_import, print_function

import click
import vmprof

def compress_stack(stack, addrspace, jit_sym):
    new_stack = []
    idx = 0
    stop_stack = False
    while idx < len(stack):
        entry = stack[idx]
        name, is_virtual, lib, offset = resolve_entry(entry, addrspace, jit_sym)
        # Skip entries in the Python runtime, but only if there is a virtual IP (Python code location) above them
        if lib and lib.name and lib.name.endswith('libpython2.7.so.1.0'):
            for tmp_idx in range(idx, len(stack)):
                tmp_entry = stack[tmp_idx]
                name, is_virtual, lib, offset = resolve_entry(tmp_entry, addrspace, jit_sym)
                # Truncate everything above Py_Main
                if name == 'Py_Main':
                    stop_stack = True
                    break
                if is_virtual:
                    idx = tmp_idx
                    entry = tmp_entry
                    break
        if stop_stack:
            break

        new_stack.append(entry)
        idx += 1

    return new_stack


def dump_stack(stack, virtual_ips, libs, addrspace, jit_sym):
    for idx,entry in enumerate(stack):
        name, addr, is_virtual, lib = addrspace.lookup(entry)
        if not lib and idx != len(stack)-1:
            if jit_sym:
                name, offset = find_jit_sym(jit_sym, addr)
                if name:
                    print ('JIT: (offset = %s)'%hex(offset),end="")
            else:
                print ('MISSING SYM:',end="")
        print (hex(entry),name, is_virtual, lib)

def resolve_entry(entry, addrspace, jit_sym):
    name, addr, is_virtual, lib = addrspace.lookup(entry)
    offset = 0
    if not lib:
        if jit_sym:
            name, offset = find_jit_sym(jit_sym, addr)
    return name, is_virtual, lib, offset

def find_jit_sym(jit_sym, addr):
    for start, size, name in jit_sym:
        if addr >= start and addr <= start+size:
            offset = addr - start
            return name, offset
    return None, 0


def dump_stacks(prof_filename, perf_filename, do_raw=False):
    period, profiles, virtual_symbols, libs, interp_name, addrspace, jit_sym = \
        vmprof.read_profile_bare(prof_filename, perf_filename=perf_filename)

    idx = 0
    for sample in profiles:
        print ("Sample %d"%idx)
        stack = sample[0]
        if not do_raw:
            stack = compress_stack(sample[0], addrspace, jit_sym)
        dump_stack(stack, virtual_symbols, libs, addrspace, jit_sym)
        print ("\n")
        idx += 1


@click.command()
@click.argument('profile', type=str)
@click.option('--perf', type=str, default='', help='Perf map file')
@click.option('--raw', is_flag=True, help='No processing of stacks')
def main(profile, perf, raw):
    dump_stacks(profile, perf, do_raw=raw)



if __name__ == '__main__':
    main()
