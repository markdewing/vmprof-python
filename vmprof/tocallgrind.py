from __future__ import absolute_import, print_function

import vmprof.reader
import vmprof.addrspace
import vmprof.dump_stacks

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


def print_callgrind_format(accum, output_filename=None):
    f = sys.stdout
    if output_filename:
        f = open(output_filename, 'w')

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
            #print('calls=%d %d'%(count, 0), file=f)
            print('calls=%d %d'%(0, 0), file=f)
            # use inclusive time for count
            print('%d %d'%(line, count), file=f)

        print('', file=f)

def do_all(prof_filename, perf_filename, remove_numba_dispatch):
    period, profiles, virtual_symbols, libs, interp_name, addrspace, jit_sym = \
        vmprof.read_profile_bare(prof_filename, perf_filename=perf_filename)

    prof_accum = collections.defaultdict(FunctionNode)

    for idx, profile in enumerate(profiles):
        stack = vmprof.dump_stacks.compress_stack(profile[0], addrspace, jit_sym, remove_numba_dispatch)
        for idx in range(len(stack)-1):
            callee_entry = stack[idx]
            entry = stack[idx+1]
            callee_name, callee_is_virtual, callee_lib, callee_offset = vmprof.dump_stacks.resolve_entry(callee_entry, addrspace, jit_sym)
            name, is_virtual, lib, offset = vmprof.dump_stacks.resolve_entry(entry, addrspace, jit_sym)

            key = get_key(name, lib)
            callee_key = get_key(callee_name, callee_lib)

            prof_accum[key].callees[callee_key] += 1
            if idx == 0:
                prof_accum[callee_key].count += 1  # exclusive (self) time

    return prof_accum


def output_callgrind(prof_filename, perf_filename, output_filename=None, remove_numba_dispatch=False):
    accum = do_all(prof_filename, perf_filename, remove_numba_dispatch)
    print_callgrind_format(accum, output_filename)

@click.command()
@click.argument('profile', type=str)
@click.option('--output',type=str, default=None, help='Output file name')
@click.option('--perf',type=str, default=None, help='Perf map file')
@click.option('--remove-numba-dispatch', is_flag=True, help='Remove Numba Dispatcher_call for clearer call graphs')
def main(profile, output, perf, remove_numba_dispatch):
    output_callgrind(profile, perf, output, remove_numba_dispatch)


if __name__ == '__main__':
    main()
