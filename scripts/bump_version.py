import os
import delegator


# File of the form
#
# 0.2.3.2
#
# First three are semvar numbers, fourth is dev release number, reset every
# time there is a version change
with open("VERSION", "r") as f:
    version = f.read().split(".")

branch = delegator.run("git symbolic-ref --short HEAD").out.rstrip()
assert branch in ["master", "dev"]

if branch == "master":
    version[1] = str(int(version[1]) + 1)
    version[3] = str(0)
elif branch == "dev":
    version[3] = str(int(version[3]) + 1)

with open("VERSION", "w") as f:
    f.write(".".join(version))

with open("PYVERSION", "w") as f:
    version[3] = f"dev{version[3]}"
    f.write(".".join(version))
