import fault.actions as actions
import os


class File:
    def __init__(self, name, tester, mode, chunk_size):
        self.name = name
        self.tester = tester
        self.mode = mode
        self.chunk_size = chunk_size
        self.name_without_ext = os.path.splitext(self.name)[0]

    def __str__(self):
        return f'File<"{self.name}">'
