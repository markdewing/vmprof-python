from __future__ import absolute_import, print_function

import vmprof.reader
import vmprof.addrspace
import vmprof.dump_stacks
import vmprof.profiler

import click
import collections
import six
import sys

class FunctionNode(object):
    def __init__(self):
        self.callees = collections.defaultdict(int) # key is (obj,file,func), value is calls # obj or file may be None
        self.count = 0  # self time

def get_key(s, lib):
    if not s:
        return (None, None, '<None>')
    if s.startswith('py:'):
        val = s.split(':')
        func = val[1]
        line = val[2]
        filename = val[3]
        #key = ('<Python>', filename, func)
        # pack the function, filename, and function starting line, following lsprofcalltree
        key = ('<Python>', filename, '%s %s:%s'%(func, filename, line))
    else:
        func = s
        obj = '<unknown>'
        if lib:
            obj = lib.name
        key = (obj, '<unknown>', func)

    return key


def print_callgrind_format(accum, output_file=None):
    f = sys.stdout
    if output_file:
        f = open(output_file, 'w')

    print("version: 1", file=f)
    print("creator: vmprof", file=f)
    print("", file=f)
    print("events: Ticks", file=f)
    total = 0
    for func_node in six.itervalues(accum):
        total += func_node.count

    print("summary: %d"%total, file=f)
    print("", file=f)
    for call_key, func_node in six.iteritems(accum):
        func_total = func_node.count
        for count in six.itervalues(func_node.callees):
            func_total += count

        obj = call_key[0]
        filename = call_key[1]
        func = call_key[2]
        if obj:
            print('ob=%s'%obj, file=f)
        if filename:
            print('fl=%s'%filename, file=f)
        print('fn=%s'%func, file=f)
        line = 0
        print('%d %d'%(line, func_node.count), file=f)  # exclusive (self) time for count

        for callee_key, count in six.iteritems(func_node.callees):
            cobj = callee_key[0]
            cfilename = callee_key[1]
            cfunc = callee_key[2]

            #exclusive time (self time) - time only in this function
            #self_count = 0
            #if accum.get(callee_key):
            #    self_count = accum.get(callee_key).count

            if cobj:
                print('cob=%s'%cobj, file=f)
            if cfilename:
                print('cfl=%s'%cfilename, file=f)
            print('cfn=%s'%cfunc, file=f)
            print('calls=%d %d'%(0, 0), file=f)
            # use inclusive time for count
            print('%d %d'%(line, count), file=f)

        print('', file=f)

def do_all(prof_file, perf_file, show_infra, python_only):

    extra_libs = []
    if perf_file:
        jit_lib = vmprof.reader.read_perf(perf_file)
        extra_libs = [jit_lib]

    lib_cache = {}
    period, profiles, virtual_symbols, libs, interp_name, addrspace = vmprof.profiler.read_profile_raw(prof_file, lib_cache, extra_libs, python_only)

    addrspace.show_infrastructure_frames(show_infra)

    filtered_profiles, addr_dict, jit_frames = vmprof.profiler.process_stacks(profiles, addrspace, interp_name, python_only)

    prof_accum = collections.defaultdict(FunctionNode)

    for idx, profile in enumerate(filtered_profiles):
        stack = list(reversed(profile[0]))

        # Remove PyPy JitAddr frames
        stack = [s for s in stack if not isinstance(s, vmprof.addrspace.JitAddr)]

        for idx in range(len(stack)-1):
            callee_entry = stack[idx]
            entry = stack[idx+1]

            callee_addr = callee_entry.addr
            addr = entry.addr
            callee_name, callee_is_virtual, callee_lib, callee_offset = addrspace.lookup(callee_addr)
            name, is_virtual, lib, offset = addrspace.lookup(addr)

            key = get_key(name, lib)
            callee_key = get_key(callee_name, callee_lib)

            prof_accum[key].callees[callee_key] += 1
            if idx == 0:
                prof_accum[callee_key].count += 1  # exclusive (self) time

    return prof_accum


def output_callgrind(prof_file, perf_file, output_file=None, show_infra=False, python_only=False):
    accum = do_all(prof_file, perf_file, show_infra, python_only)
    print_callgrind_format(accum, output_file)

@click.command()
@click.argument('profile', type=str)
@click.option('--output',type=str, default=None, help='Output file name')
@click.option('--perf',type=str, default=None, help='Perf map file')
@click.option('--show_infra', is_flag=True, help='Show infrastructure frames in call graphs')
@click.option('--python_only', is_flag=True, help='Show only Python frames')
def main(profile, output, perf, show_infra, python_only):
    output_callgrind(profile, perf, output, show_infra, python_only)


if __name__ == '__main__':
    main()
