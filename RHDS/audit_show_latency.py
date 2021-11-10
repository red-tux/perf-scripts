#!/bin/env python

import sys
import re
from datetime import datetime

r_ldif = re.compile("^ (.*)")
r_attr = re.compile("^(\w*): (.*)")
r_dn = re.compile("^dn: (.*)")
r_entry_time = re.compile("^time: (.*)")
r_modify_time = re.compile("^modifyTimestamp: (.*)")
r_changetype = re.compile("^changetype: (.*)")

entry=[]

try:
  for line in iter(sys.stdin.readline, b''):
    st_line=line.rstrip()
    if line=="\n":  
      dn = ""
      ent_time = ""
      mod_time = ""
      change_type = ""
      # Iterate entry for dn and time  
      for l in entry:
        m_attr = r_attr.match(l)
        if m_attr:
          attr_name = m_attr.group(1)
          attr_val = m_attr.group(2)
          if attr_name == "dn":
            dn = attr_val
          elif attr_name == "time":
            ent_time = attr_val
          elif attr_name == "modifyTimestamp":
            mod_time = attr_val
          elif attr_name == "changetype":
            change_type = attr_val

      ent_time_parsed = datetime.strptime(ent_time,"%Y%m%d%H%M%S")
      print("{}  {}".format(change_type,dn))
      print("Log timestamp: {}".format(ent_time_parsed))
      if mod_time:
        mod_time_parsed = datetime.strptime(mod_time,"%Y%m%d%H%M%SZ")
        time_diff = int((mod_time_parsed-ent_time_parsed).total_seconds())
        print("Mod timestamp: {}    ({})".format(mod_time_parsed,time_diff))
      entry=[]
      print
    else:
      m_ldif = r_ldif.match(st_line)
      if m_ldif:
        entry[-1]=entry[-1] + m_ldif.group(1)
      else:
        entry.append(st_line)

except KeyboardInterrupt:
  sys.stdout.flush()
  pass