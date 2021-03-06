#!/usr/bin/python

import os
import sys
import re

from . transform import SymbioticCC
from . verifier import SymbioticVerifier
from . options import SymbioticOptions
from . utils import err, dbg, print_elapsed_time, restart_counting_time
from . utils.utils import print_stdout
from . utils.process import ProcessRunner
from . exceptions import SymbioticExceptionalResult

class Symbiotic(object):
    """
    Instance of symbiotic tool. Instruments, prepares, compiles and runs
    symbolic execution on given source(s)
    """

    def __init__(self, tool, src, opts=None, env=None):
        # source file
        self.sources = src
        # source compiled to llvm bytecode
        self.curfile = None
        # environment
        self.env = env

        if opts is None:
            self.options = SymbioticOptions()
        else:
            self.options = opts

        # tool to use
        self._tool = tool

    def terminate(self):
        pr = ProcessRunner()
        if pr.hasProcess():
            pr.terminate()

    def kill(self):
        pr = ProcessRunner()
        if pr.hasProcess():
            pr.kill()

    def kill_wait(self):
        pr = ProcessRunner()
        if not pr.hasProcess():
            return

        if pr.exitStatus() is None:
            from time import sleep
            while pr.exitStatus() is None:
                pr.kill()

                print('Waiting for the child process to terminate')
                sleep(0.5)

            print('Killed the child process')

    def replay_nonsliced(self, cc):
        bitcode = cc.prepare_unsliced_file()
        params = []
        if hasattr(self._tool, "replay_error_params"):
            params = self._tool.replay_error_params(cc.curfile)

        print_stdout('INFO: Replaying error path', color='WHITE')
        restart_counting_time()

        verifier = SymbioticVerifier(bitcode, self.sources,
                                     self._tool, self.options,
                                     self.env, params)
        res = verifier.run()

        print_elapsed_time('INFO: Replaying error path time', color='WHITE')

        return res

    def _run_symbiotic(self):
        cc = SymbioticCC(self.sources, self._tool, self.options, self.env)
        bitcode = cc.run()

        if self.options.no_verification:
            return 'No verification'

        verifier = SymbioticVerifier(bitcode, self.sources,
                                     self._tool, self.options, self.env)
        res = verifier.run()

        # if we crashed on the sliced file, try running on the unsliced file
        # (do this optional, as well as for slicer and instrumentation)
        if not self.options.noslice and \
           (self.options.sv_comp or self.options.test_comp) and \
            res.lower().startswith('error') or res.lower().startswith('unknown'):
            print_stdout("INFO: Failed on the sliced code, trying on the unsliced code",
                         color="WHITE")
            bitcode = cc.prepare_unsliced_file()
            verifier = SymbioticVerifier(bitcode, self.sources,
                                         self._tool, self.options, self.env)
            res = verifier.run()
            self.options.replay_error = False # now we do not need to replay the error
            print_elapsed_time('INFO: Running on unsliced code time', color='WHITE')

        if self.options.replay_error and\
           not self._tool.can_replay():
           dbg('Replay required but the tool does not support it')

        has_error = res and\
                    (res.startswith('false') or\
                    (res.startswith('done') and self.options.property.errorcall()))
        if has_error and self.options.replay_error and\
           not self.options.noslice and self._tool.can_replay():
            print_stdout("Trying to confirm the error path")
            newres = self.replay_nonsliced(cc)

            dbg("Original result: '{0}'".format(res))
            dbg("Replayed result: '{0}'".format(newres))

            if res != newres:
                # if we did not replay the original error, but we found a different error
                # on this path, report it, since it should be real
                if self.options.sv_comp or self.options.test_comp:
                    has_error = newres and\
                                (newres.startswith('false') or\
                                (newres.startswith('done') and\
                                 self.options.property.errorcall()))
                    if has_error:
                        res = newres
                    else:
                        res = 'cex not-confirmed'
                        has_error = False
                else:
                    res = 'cex not-confirmed'
                    has_error = False

        if has_error and hasattr(self._tool, "describe_error"):
            self._tool.describe_error(cc.curfile)

        if has_error and self.options.executable_witness and\
           hasattr(self._tool, "generate_exec_witness"):
            self._tool.generate_exec_witness(cc.curfile, self.sources)

        if not self.options.nowitness and hasattr(self._tool, "generate_witness"):
            self._tool.generate_witness(cc.curfile, self.sources, has_error)

        return res

    def run(self):
        try:
            return self._run_symbiotic()
        except KeyboardInterrupt:
            self.terminate()
            self.kill()
            print('Interrupted...')
            return 'interrupted'
        except SymbioticExceptionalResult as res:
            # we got result from some exceptional case
            return str(res)

