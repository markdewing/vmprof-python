import vmprof
import tempfile

from vmprof.addrspace import AddressSpace
from vmprof.stats import Stats
from vmprof.reader import read_prof, LibraryData


class VMProfError(Exception):
    pass

class ProfilerContext(object):
    done = False

    def __init__(self):
        self.tmpfile = tempfile.NamedTemporaryFile()

    def __enter__(self):
        vmprof.enable(self.tmpfile.fileno(), 0.001)

    def __exit__(self, type, value, traceback):
        vmprof.disable()
        self.done = True


def read_profile_raw(prof_filename, lib_cache, extra_libs=None,
                 virtual_only=True, include_extra_info=True):
    prof = open(str(prof_filename), 'rb')

    period, profiles, virtual_symbols, libs, interp_name = read_prof(prof)

    if interp_name == 'pypy':
        virtual_only = True

    if not virtual_only or include_extra_info:
        exe_name = libs[0].name
        for lib in libs:
            executable = lib.name == exe_name
            if lib.name in lib_cache:
                lib.get_symbols_from(lib_cache[lib.name], executable)
            else:
                lib.read_object_data(executable)
                lib_cache[lib.name] = lib
    libs.append(
        LibraryData(
            '<virtual>',
            0x7000000000000000,
            0x7fffffffffffffff,
            True,
            symbols=virtual_symbols)
    )
    if extra_libs:
        libs += extra_libs
    addrspace = AddressSpace(libs)

    return period, profiles, virtual_symbols, libs, interp_name, addrspace


def process_stacks(profiles, addrspace, interp_name, virtual_only, include_extra_info=True):
    addr_dict = {}
    filtered_profiles, addr_set, jit_frames = addrspace.filter_addr(profiles,
        virtual_only, interp_name)

    for addr in addr_set:
        name, _, _, lib = addrspace.lookup(addr)
        if lib is None:
            name = 'jit:' + name
        addr_dict[addr] = name

    if include_extra_info:
        addr_dict.update(addrspace.meta_data)

    return filtered_profiles, addr_dict, jit_frames


def read_profile_stacks(prof_filename, lib_cache, extra_libs=None,
                 virtual_only=True, include_extra_info=True):

    period, profiles, virtual_symbols, libs, interp_name, addrspace = read_profile_raw(prof_filename, lib_cache, extra_libs, virtual_only, include_extra_info)

    filtered_profiles, addr_dict, jit_frames = process_stacks(profiles, addrspace, interp_name, virtual_only, include_extra_info)

    return filtered_profiles, addr_dict, jit_frames, interp_name


# lib_cache is global on purpose
def read_profile(prof_filename, lib_cache={}, extra_libs=None,
                 virtual_only=True, include_extra_info=True):
    filtered_profiles, d, jit_frames, interp_name = read_profile_stacks(prof_filename, lib_cache, extra_libs, virtual_only, include_extra_info)

    s = Stats(filtered_profiles, d, jit_frames, interp_name)
    return s


class Profiler(object):
    ctx = None

    def __init__(self):
        self._lib_cache = {}

    def measure(self):
        self.ctx = ProfilerContext()
        return self.ctx

    def get_stats(self):
        if not self.ctx:
            raise VMProfError("no profiling done")
        if not self.ctx.done:
            raise VMProfError("profiling in process")
        res = read_profile(self.ctx.tmpfile.name)
        self.ctx = None
        return res

