
import os, os.path
import re
import sys

logf = None
base_dn = None
entry = []
follow = False

r_ldif = re.compile("^ (.*)")
r_dn = re.compile("^dn: (.*)")
r_base = None
r_entry_time = re.compile("^time: (.*)")

def pre(plugargs):
  global logf
  global base_dn
  global r_base
  global follow

  logfile = plugargs.get('logfile', None)
  if not logfile:
    print("Error Missing require argument filter_audit_log.logfile")
    return False
  base_dn = plugargs.get('basedn', None)
  if not base_dn:
    print("Error Missing require argument filter_audit_log.basedn")
    return False
  follow = plugargs.get('follow', False)
  if not isinstance(follow,bool):
    follow = True
  r_base = re.compile("(.*),{}".format(base_dn))

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
  global entry_dn

  st_line=line.rstrip()

  if follow:
    print("Line: {}".format(st_line))

  if line=="\n":  
    dn=""
    ent_time=""
    # Iterate entry for dn and time  
    for l in entry:
      m_dn = r_dn.match(l)
      m_time = r_entry_time.match(l)
      if m_dn:
        dn = m_dn.group(1)
      if m_time:
        ent_time = m_time.group(1)

      if dn and ent_time:
        break

    # do we have a complete entry?
    if dn and ent_time:
      dn_match = r_base.match(dn)

      # m_dn = any(r_dn.match(l) for l in entry)
      if dn_match:
        print("Matched DN: {} {:4d} {}".format(ent_time,len(entry),dn))
        logf.write("\n".join(entry))
        logf.write('\n\n')
        logf.flush()
      else:
        print(" Unmatched: {} {:4d} {}".format(ent_time,len(entry),dn))
    else:
      print("Discarding entry, no dn or time value found")
    
    # Done processing separator, reset the entry array
    entry=[]
    return True
  else:
    m_ldif = r_ldif.match(st_line)
    if m_ldif:
      entry[-1]=entry[-1] + m_ldif.group(1)
    else:
      entry.append(st_line)
    return True

  # we should never get here
  print("We weren't supposed to get here")
  return False
