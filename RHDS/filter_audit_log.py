
import os, os.path
import re
import sys

logf = None
base_dn = None
entry = None

def pre(plugargs):
  global logf
  global base_dn
  logfile = plugargs.get('logfile', None)
  if not logfile:
    print("Error Missing require argument filter_audit_log.logfile")
    return False
  base_dn = plugargs.get('basedn', None)
  if not base_dn:
    print("Error Missing require argument filter_audit_log.basedn")
    return False

  needchmod = False
  if not os.path.isfile(logfile): needchmod = True
  if sys.version_info < (3, 0):
    logf = open(logfile, 'a', 0) # 0 for unbuffered output
  else:
    logf = open(logfile, 'a')
  if needchmod: os.chmod(logfile, 0o600)
  return True

def post():
    global logf
    logf.close()
    logf = None


def plugin(line):
  global entry

  print("Line: '{}'".format(line))
  if line=="\n":
    logf.write(entry + "\n")
    logf.flush()
    return True
  else:
    entry += line
    return True

  # we should never get here
  print("We weren't supposed to get here")
  return False
