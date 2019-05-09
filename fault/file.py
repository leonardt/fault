import fault.actions as actions
import os


class File:
    def __init__(self, name, tester, mode, chunk_size):
        self.name = name
        self.tester = tester
        self.mode = mode
        self.chunk_size = chunk_size
        basename = os.path.basename(self.name)
        filename = os.path.splitext(basename)[0]
        filename = filename.replace(".", "_")
        self.name_without_ext = filename

    def __str__(self):
        return f'File<"{self.name}">'
