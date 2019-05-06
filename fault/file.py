import fault.actions as actions


class File:
    def __init__(self, file_name, tester):
        self.file_name = file_name
        self.tester = tester

    def __str__(self):
        return f'File<"{self.file_name}">'

    def read(self, n_char=1):
        return actions.FileRead(self, n_char)

    def write(self, value, n_char=1):
        self.tester.actions.append(actions.FileWrite(self, value, n_char))
