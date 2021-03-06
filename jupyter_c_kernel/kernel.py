from queue import Queue
from threading import Thread

from ipykernel.kernelbase import Kernel
import re
import subprocess
import tempfile
import os
import os.path as path


class RealTimeSubprocess(subprocess.Popen):
    """
    A subprocess that allows to read its stdout and stderr in real time
    """

    def __init__(self, cmd, write_to_stdout, write_to_stderr):
        """
        :param cmd: the command to execute
        :param write_to_stdout: a callable that will be called with chunks of data from stdout
        :param write_to_stderr: a callable that will be called with chunks of data from stderr
        """
        self._write_to_stdout = write_to_stdout
        self._write_to_stderr = write_to_stderr

        super().__init__(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

        self._stdout_queue = Queue()
        self._stdout_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stdout, self._stdout_queue))
        self._stdout_thread.daemon = True
        self._stdout_thread.start()

        self._stderr_queue = Queue()
        self._stderr_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stderr, self._stderr_queue))
        self._stderr_thread.daemon = True
        self._stderr_thread.start()

    @staticmethod
    def _enqueue_output(stream, queue):
        """
        Add chunks of data from a stream to a queue until the stream is empty.
        """
        for line in iter(lambda: stream.read(4096), b''):
            queue.put(line)
        stream.close()

    def write_contents(self):
        """
        Write the available content from stdin and stderr where specified when the instance was created
        :return:
        """

        def read_all_from_queue(queue):
            res = b''
            size = queue.qsize()
            while size != 0:
                res += queue.get_nowait()
                size -= 1
            return res

        stdout_contents = read_all_from_queue(self._stdout_queue)
        if stdout_contents:
            self._write_to_stdout(stdout_contents)
        stderr_contents = read_all_from_queue(self._stderr_queue)
        if stderr_contents:
            self._write_to_stderr(stderr_contents)


class CKernel(Kernel):
    implementation = 'jupyter_c_kernel'
    implementation_version = '1.0'
    language = 'c'
    language_version = 'C11'
    language_info = {'name': 'c',
                     'mimetype': 'text/plain',
                     'file_extension': '.c'}
    banner = "C kernel.\n" \
             "Uses gcc, compiles in C11, and creates source code files and executables in temporary folder.\n"

    def __init__(self, *args, **kwargs):
        super(CKernel, self).__init__(*args, **kwargs)
        self.files = []
        mastertemp = tempfile.mkstemp(suffix='.out')
        os.close(mastertemp[0])
        self.master_path = mastertemp[1]
        filepath = path.join(path.dirname(path.realpath(__file__)), 'resources', 'master.c')
        subprocess.call(['gcc', filepath, '-rdynamic', '-ldl',
            '-ggdb', '-fPIC', '-ftrapv', '-fpack-struct', '-shared',
            '-rdynamic', '-fsanitize=address', '-fsanitize=leak', '-fsanitize=undefined',
            '-fsanitize=shift', '-fsanitize=vla-bound', '-fsanitize=null',
            '-fsanitize=bounds', '-fsanitize=object-size',
            '-fsanitize-address-use-after-scope', '-fstack-protector-all', '-o', self.master_path])

    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for file in self.files:
            os.remove(file)
        os.remove(self.master_path)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
        return file

    def _write_to_stdout(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def create_jupyter_subprocess(self, cmd, input_text=""):
        return RealTimeSubprocess(cmd,
                                  lambda contents: self._write_to_stdout(contents.decode()),
                                  lambda contents: self._write_to_stderr(contents.decode()))

    def compile_with_gcc(self, source_filename, binary_filename, cflags=None, ldflags=None):
        # ggdb -> Maximum debugging information level
        # fPIC -> Position Independant Code, required for dynamic loading
        # rdynamic -> Allows dlopen to open the compiled result as a process by adding all symbols.
        # shared -> Make a shared object which can be linked to make an executable. Needed for rdynamic iirc.
        # fpack-struct -> No padding is present in structs.
        # fsanitize=address -> turn on address sanitisation, used to detect memory errors where possible.
        # fsanitize=leak -> detect memory leaks using address sanatiser.
        # fsanitize=undefined -> turn on undefined behaviour sanitizer.
        # fsanitize=shift -> check for undefined bit shift errors.
        # fsanitize=vla-bound -> check for negative length variable length arrays.
        # fsanitize=null -> check for NULL pointer dereferences.
        # fsanitize=bounds -> check array bounds where possible.
        # fsanitize=object-size -> check memory references don't overflow their allocated size.
        # fsanitize-address-use-after-scope -> this shouldn't come up, but in nested scopes,
        #     variables local to one nested scope are not accessible (even by pointers) in another,
        # fstack-protector-all -> protects against a few redirection attacks.

        cflags = ['-ggdb', '-fPIC', '-ftrapv', '-fpack-struct',
            '-fsanitize=address', '-fsanitize=leak', '-fsanitize=undefined',
            '-fsanitize=shift', '-fsanitize=vla-bound', '-fsanitize=null',
            '-fsanitize=bounds', '-fsanitize=object-size',
            '-fsanitize-address-use-after-scope', '-fstack-protector-all'] + cflags
        args = ['gcc', source_filename] + cflags + ['-o', binary_filename] + ldflags
        return self.create_jupyter_subprocess(cmd=args)

    def _filter_magics(self, code):

        magics = {'cflags': [],
                  'ldflags': [],
                  'stdin': "",
                  'stdout': "",
                  'memtotalnoterm': "",
                  'memtotal': "",
                  'memaux': "",
                  'memexpect': "",
                  'test_script': [],
                  'args': []}

        for line in code.splitlines():
            if line.startswith('//%'):
                try:
                    key, value = line[3:].split(":", 2)
                    key = key.strip().lower()
                except ValueError:
                    # Don't want kernel to fail because an error was made in source code comment.
                    continue

                if key in ['ldflags', 'cflags']:
                    for flag in value.split():
                        magics[key] += [flag]
                elif key == "stdin":
                    # Could probably be a match instead,
                    # but this is easier for now.
                    # Note: this is very basic, string escapes and the like
                    #   aren't included.
                    for stringContents in re.findall(r'\s*"([^"]*)"', value):
                        magics['stdin'] += stringContents + "\n"
                elif key == "stdout":
                    # Could probably be a match instead,
                    # but this is easier for now.
                    # Note: this is very basic, string escapes and the like
                    #   aren't included.
                    for stringContents in re.findall(r'\s*"([^"]*)"', value):
                        magics['stdout'] += stringContents + "\n"
                elif key == "test_script":
                    magics['test_script'].append(value)
                elif key == "memtotalnoterm":
                    magics['memtotalnoterm'] += "If you only allocated " + value + " bytes, you have likely left off space for string termination.\n"
                elif key == "memtotal":
                    magics['memtotal'] += "If you only allocated " + value + " bytes, you may not have allocated space for the array, which may or may not be what you wanted to do.\n"
                elif key == "memaux":
                    magics['memaux'] += "If you only allocated " + value + " bytes, you may not have allocated space for each string in the array, only the pointers to each string.\n"
                elif key == "memexpect":
                    magics['memexpect'] += "You should expect to use about " + value + " bytes, you can use valgrind and gdb to check that you've got this right in next week's workshop.\n"
                elif key == "args":
                    # Split arguments respecting quotes
                    for argument in re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', value):
                        magics['args'] += [argument.strip('"')]

        return magics

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):

        magics = self._filter_magics(code)

        with self.new_temp_file(suffix='.c') as source_file:
            source_file.write(code)
            source_file.flush()
            with self.new_temp_file(suffix='.out') as binary_file:
                p = self.compile_with_gcc(source_file.name, binary_file.name, magics['cflags'], magics['ldflags'])
                while p.poll() is None:
                    p.write_contents()
                p.write_contents()
                if p.returncode != 0:  # Compilation failed
                    self._write_to_stderr("Kernel location: " + os.path.dirname(os.path.realpath(__file__)) + "\n")
                    self._write_to_stderr(
                            "[C kernel] GCC exited with code {}, the executable will not be executed".format(
                                    p.returncode))
                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}

        #p = self.create_jupyter_subprocess([self.master_path, binary_file.name] + magics['args'])
        # We deviate here to get sanitization at the cost of responsive output.
        p = self.create_jupyter_subprocess(cmd=([binary_file.name] + magics['args']))
        if magics['stdin'] != "":
            self._write_to_stderr(("input: " + magics['stdin']))
        if magics['stdout'] != "":
            self._write_to_stderr(("expected output: " + magics['stdout']))
        if magics['memtotalnoterm'] != "" or magics['memtotal'] != "" or magics['memaux'] != "" or magics['memexpect'] != "":
            self._write_to_stderr("Some memory hints which you might like to verify for this question:\n")
        if magics['memtotalnoterm'] != "":
            self._write_to_stderr(magics['memtotalnoterm'])
        if magics['memtotal'] != "":
            self._write_to_stderr(magics['memtotal'])
        if magics['memaux'] != "":
            self._write_to_stderr(magics['memaux'])
        if magics['memexpect'] != "":
            self._write_to_stderr(magics['memexpect'])
        p.stdin.write(magics['stdin'].encode(encoding="utf-8", errors="strict"))
        p.stdin.close()
        while p.poll() is None:
            p.write_contents()
        p.write_contents()

        if p.returncode != 0:
            self._write_to_stderr("[C kernel] Executable exited with code {}".format(p.returncode))

        if len(magics['test_script']) > 0:
            for item in magics['test_script']:
                self._write_to_stderr("Testing with script: " + item + ".\n")
                subproc_commands = [['chmod'] + ['777'] + [item]] + [['/bin/bash'] + [item] + [binary_file.name]]
                for subproc_command in subproc_commands:
                    self._write_to_stderr("Command: " + str(subproc_command) + '\n')
                    test_process = self.create_jupyter_subprocess(cmd=subproc_command)
                    while test_process.poll() is None:
                        test_process.write_contents()
                    test_process.write_contents()

        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}

    def do_shutdown(self, restart):
        """Cleanup the created source code files and executables when shutting down the kernel"""
        self.cleanup_files()
