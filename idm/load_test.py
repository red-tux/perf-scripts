#!/bin/env python3

# Steps requried to use
# install requried libraries
# (root)# dnf install python3-ldap3
#
# Create python virtual environment directory
# (user)$ python3 -m venv ./venv3
#
# Enable virtual environment
# (user)$ source ./venv3/bin/activate
#
# Update pip and then install needed libary
# (user-venv3)$ pip install --upgrade pip
# (user-venv3)$ pip install python-freeipa
# (user-venv3)$ pip install ldap3
#
# Execute Script:
# (user-venv3)$ ./load_test.py -h

# -- not required, saved as a note
# dnf install python3-requests-kerberos python3-requests-gssapi


import sys
import time
from datetime import datetime
import re
import argparse
import logging
#from linetimer import CodeTimer
import itertools
import pprint
import subprocess

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# from ldap3 import Server, Connection, ALL, MODIFY_ADD
import ldap3

from python_freeipa import ClientMeta
# import requests
#from requests_kerberos import HTTPKerberosAuth

# generate a 4 digit randomizer from the current time
# randomizer = int(time.time()) % 10000
randomizer = datetime.now().strftime("%d%H%M")
start_timestr = datetime.now().strftime("%Y%m%d %H:%M")
start_time = time.time()
uid_template = "tuser{}_{{seq}}".format(randomizer)

pp=pprint.PrettyPrinter(indent=2)

class LogFilter(object):
    def __init__(self,level,type='ge'):
      self.__level = level
      self.__type = type
    
    def filter(self, logRecord):
      if self.__type == 'ge':
        return logRecord.levelno >= self.__level
      elif self.__type == 'eq':
        return logRecord.levelno == self.__level
      else:
        return logRecord.levelno <= self.__level

class MyLogger(logging.getLoggerClass()):
  _PERF = 21

  def __init__(self, name, **kwargs ):
    super().__init__(name, **kwargs)

    logging.addLevelName(self._PERF, 'PERF')

  def perf(self, message, *args, **kwargs):
    if self.isEnabledFor(self._PERF):
      self._log(self._PERF, message, args, **kwargs)

logging.setLoggerClass(MyLogger)

logger = logging.getLogger('IDM_user_load_tester')
logger.setLevel(logging.INFO)

_stout_handler = logging.StreamHandler()
_stout_handler.setLevel(logging.INFO)
logger.addHandler(_stout_handler)



def iter_timer(iterable, step=10, label=""):
  start = time.time()
  last_t = start
  loop_tag = "loop {}{}{{}}".format(label, " "*bool(label))  
  logger.perf(loop_tag.format("start"))
  pos = 0
  # step_count=len(iterable)//step
  for item in iterable:
    pos = pos + 1
    if pos != 0 and pos % step == 0:
      logger.perf("{}: {:4.3f}  {:4.3f}".format(item,time.time() - start, time.time() - last_t))
      last_t = time.time()
    yield item
  logger.perf("{}: {:4.3f}  {:4.3f}".format(pos,time.time() - start, time.time() - last_t))
  logger.perf(loop_tag.format("end"))

def loop_timer(count,step=10,label=""):
  start = time.time()
  last_t = start
  loop_tag = "loop {}{}{{}}".format(label, " "*bool(label))
  logger.perf(loop_tag.format("start"))
  for item in range(count):
    if item != 0 and item % step == 0:
      logger.perf("{}: {:4.3f}  {:4.3f}".format(item,time.time() - start, time.time() - last_t))
      last_t = time.time()
    yield item
  logger.perf("{}: {:4.3f}  {:4.3f}".format(count,time.time() - start, time.time() - last_t))
  logger.perf(loop_tag.format("end"))

# creates a generator to iterate through a list in chunks
# returns an iterator chunk of the iterable of up to the given size.
def chunker(iterable, size):
  it = iter(iterable)
  while True:
    chunk = tuple(itertools.islice(it,size))
    if not chunk:
      return
    yield chunk

def generate_user(seq_num, ldif_out=False, dc_dn=None):
  #create a list/dict of user entries to use for passing to a function
  user = {}
  user["a_uid"] = uid_template.format(seq=seq_num)
  user["o_givenname"] = str(seq_num)
  user["o_sn"] = "tuser_{}".format(randomizer)
  user["o_cn"] = "{} {}".format(user["o_givenname"], user["o_sn"])
  user["o_preferredlanguage"]='EN'
  user["o_employeetype"]="Created via load_test.py.  Run started at: {}".format(start_timestr)
  
  # if the user is to be used for LDIF, strip the first two prepended chars
  if ldif_out:
    clean_rex = r"^._"
    keylist = list(user.keys())
    user['attributes']={}
    for key in keylist:
      new_key = re.sub(clean_rex,'',key)
      user['attributes'][new_key]=user[key]
      del user[key]
    if dc_dn is not None:
      user['dn']="uid={},cn=staged users,cn=accounts,cn=provisioning,{}".format(user['attributes']['uid'],dc_dn)
    user['object_class']=['top','inetorgperson']

  return user


def add_users_api(total):
  users=[]
  for i in loop_timer(args.count,args.count//10,label="user_add_api"):
    user = generate_user(i)
    users.append(user["a_uid"])
    logger.debug(user)

    if args.stage:
      user_out = client.stageuser_add(**user)
    else:
      user_out = client.user_add(**user)
    logger.debug(user_out)

  return users

def add_users_stage(total):
  users=[]
  if args.ldap_stage:
    for i in loop_timer(args.count,args.count//10,label="user_add_stage_ldap"):
      user = generate_user(i, ldif_out=True, dc_dn=dom_dn)
      users.append(user['attributes']['uid'])
      user_dn=user['dn']
      del user['dn']
      ldap_conn.add(user_dn,**user)

  else:
    for i in loop_timer(args.count,args.count//10,label="user_add_stage"):
      user = generate_user(i)
      users.append(user["a_uid"])
      logger.debug(user)

      user_out = client.stageuser_add(**user)
      logger.debug(user_out)

  for i in iter_timer(users,args.count//10,label="user_activate"):
    activate_out = client.stageuser_activate(i)
    logger.debug(activate_out)
        

  return users

def get_users(template):
  logger.perf("Checking for user template '{}'".format(template))

  if client.user_find(template,o_sizelimit=1)['count'] > 0:
    users = [ user['uid'][0] for user in client.user_find(template,o_sizelimit=0,o_timelimit=0)['result']]
    logger.perf("Found {} users".format(len(users)))
  else:
    logger.perf("Unable to find user template")
    exit(1)

  return users
  
def get_users_ldap(template):
  logger.perf("Checking for user template '{}'".format(template))

  results = client.user_find(template,o_sizelimit=1)
  if results['count'] > 0:
    result=results['result'][0]
    uid = result['uid'][0]
    user_dn=result['dn']
    base_dn = re.sub("uid={},".format(uid),'',user_dn)
    entry_gen = ldap_conn.extend.standard.paged_search(search_base = base_dn,
                                                          search_filter = "(uid={}*)".format(template),
                                                          search_scope = ldap3.SUBTREE,
                                                          attributes = '*',
                                                          paged_size=1000,
                                                          generator=True)

    total = 0
    users=[]
    for entry in entry_gen:
      # print(entry)
      total += 1
      if total % 10000 == 0:
        logger.perf("Loaded {} users".format(total))
      # extract user uid.  For some reason uid is a list, we only need the first
      users.append(entry['attributes']['uid'][0])
      if args.user_limit>-1 and total >= args.user_limit:
        break

    logger.perf("Loaded {} users".format(len(users)))
  else:
    logger.perf("Unable to find user template")
    exit(1)

  return users

def create_group_add_users_api(i,users):
  group_name = "group{}_{}".format(randomizer,i)
  group_desc = "Test group vor load_test.py.  Run started at: {}".format(start_timestr)

  logger.info("Creating group: {}".format(group_name))
  result = client.group_add(group_name, o_description=group_desc)
  if result["value"]==group_name:
    logger.info("Success")
  logger.debug(result)

  logger.perf("Group: {}".format(group_name))
  
  logger.info("Adding {} users".format(len(users)))
  result = client.group_add_member(group_name, o_user=users)
  logger.info("Done")
  logger.debug(result)


def create_group_add_users_ldap(i,users,ldap_conn,base_user_dn,chunk=-1):
  group_name = "group{}_{}".format(randomizer,i)
  group_desc = "Test group vor load_test.py.  Run started at: {}".format(start_timestr)

  logger.info("Creating group: {}".format(group_name))
  result = client.group_add(group_name, o_description=group_desc,o_raw=True)
  group_dn=result['result']['dn']

  logger.debug(result)

  mod_group_users_ldap(users, ldap_conn, base_user_dn, group_dn, ldap3.MODIFY_ADD, chunk)


def remove_group_users_ldap(users, ldap_conn, base_user_dn, group_name, group_dn, chunk=-1):
  logger.info("Group to delete: {}".format(group_dn))
  start = time.time()
  mod_group_users_ldap(users, ldap_conn, base_user_dn, group_dn, ldap3.MODIFY_DELETE, chunk)
  logger.perf("Removing users from group took: {:4.3f}".format(time.time() - start))
  result = client.group_show(group_name)
  logger.info("Group show: {}".format(result))
  logger.info("Delete group from IDM: {}".format(group_dn))
  start = time.time()
  result = client.group_del(group_name)
  logger.perf("Delete group using API took: {:4.3f}".format(time.time() - start))
  logger.info("Group del resul: {}".format(result))

def ldap_modify_retry(*fargs, **kwargs):
  for retry_num in range(args.max_retries+1):
    try:
      return(ldap_conn.modify(*fargs,**kwargs))
    except Exception as e:
      logger.perf("Exception Occured")
      logger.perf("'{}'".format(e))
      logger.perf("{} retries left".format(args.max_retries-retry_num))
      ldap_conn.unbind()
      ldap_conn.bind()
      logger.info("LDAP Connection rebound")


def mod_group_users_ldap(users, ldap_conn, base_user_dn, group_dn, ldap_mod_op, chunk=-1):
  if chunk==-1:
    chunk=len(users)

  user_dn_list = ["uid={},{}".format(user,base_user_dn) for user in users]

  for user_dn_chunk in chunker(user_dn_list,chunk):
    # print(user_dn_chunk)

    logger.perf("Chunk ({})".format(len(user_dn_chunk)))
    logger.debug(user_dn_chunk)

    # result = ldap_conn.modify(group_dn,{"member":[(ldap_mod_op, user_dn_chunk)]})
    result = ldap_modify_retry(group_dn,{"member":[(ldap_mod_op, user_dn_chunk)]})
    logger.debug(ldap_conn.usage)
    logger.debug("LDAP Modify result: {}".format(result))

    if args.rebind:
      logger.perf("rebinding LDAP connection")
      ldap_conn.unbind()
      ldap_conn.bind()
    logger.debug("LDAP Modify result: {}".format(result))
      



    if args.delay>0:
      logger.perf("Sleeping {} seconds".format(args.delay))
      time.sleep(args.delay)


parser = argparse.ArgumentParser(description="Generate load test data for IdM",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-v', dest='verbosity', action='count', default=0,
                    help="Increase Verbosity, default is errors only.  Only effective up to 3 levels.")
parser.add_argument('-c', type=int, dest='count',
                    help="Total count of users to add")
parser.add_argument('-g', dest='group_count', default=1, type=int,
                    help="Number of groups to create")
parser.add_argument('-S', dest='server', type=str,
                    help="Server to connect to")
parser.add_argument('-U', dest='user', type=str,
                    help="User account to use for connect")
parser.add_argument('-P', dest='password', type=str,
                    help="Password for connection")
parser.add_argument('--stage', dest='stage', action='store_true', default=False,
                    help="Create user in stage not active")
parser.add_argument('--stage-ldap', dest='ldap_stage', default=False, action='store_true',
                    help='Create stage users via ldap not API')
parser.add_argument('--ldap-group', dest='ldap_group', default=False, action='store_true',
                    help="Add users to group using LDAP directly")
parser.add_argument('--ldap-group-remove', dest='ldap_group_del', type=str,
                    help="Remove users from group using LDAP directly")
parser.add_argument('-C', dest='chunk', type=int, default=-1,
                    help="Chunk size for batching user adds to groups, -1 means all users given in count")
parser.add_argument('-r', dest='reuse_template', type=str,
                    help="Reuse existing users for group add using given user naming template")                    
parser.add_argument('-D', dest='delay',type=int, default=0,
                    help="Delay N seconds between chunks")                    
parser.add_argument('--rebind', dest='rebind',default=False,action='store_true',
                    help="Perform a unmind/bind operation between ldap operations.")
parser.add_argument('-l', dest='user_limit', type=int, default=-1,
                    help="Limit the number of users returned by reuse")
parser.add_argument('--max-retries',dest='max_retries', type=int, default=0,
                    help="Maximum number of retries for a failed chunk operation")

args=parser.parse_args()

# setting up logger here to prevent log files being generated when showing help

perf_logfile = "perf_{}".format(randomizer)
_perf_handler = logging.FileHandler(perf_logfile)
_perf_formatter = logging.Formatter("%(asctime)s; %(message)s")
_perf_handler.setFormatter(_perf_formatter)
_perf_handler.addFilter(LogFilter(MyLogger._PERF,type='eq'))
logger.addHandler(_perf_handler)

if args.verbosity:
  # Error is a level of 40.  
  level=30-(args.verbosity*10)
  if level<0:
    level=0
  logger.setLevel(level)
  levels={ 5: "CRITICAL",
           4: "ERROR",
           3: "WARNING",
           2: "INFO",
           1: "DEBUG",
           0: "ALL" }
  if level!=30:
    log_file = "log_{}".format(randomizer)
    _file_handler = logging.FileHandler(log_file)
    _file_formatter = logging.Formatter('%(asctime)s %(levelname)s :: %(message)s')
    _file_handler.setFormatter(_file_formatter)
    _file_handler.addFilter(LogFilter(level))
    logger.addHandler(_file_handler)
    logger.info("Logging to file '{}'".format(log_file))
    logger.info("Debug level: {0} ({1})".format(levels[level // 10],level))

# client = ClientMeta('ipaserver0.example.com',False)
# client.login('admin', 'admin123')
# kerberos seems broken using OS rpms on RHEL 8
#client.login_kerberos()
# user = client.user_add('test4', 'John', 'Doe', 'John Doe', o_preferredlanguage='EN')

# Output some data to the user about the script options passed in
# Not working as expected when git not found
try:
  commit_info = str(subprocess.check_output(['git', 'log', '-n', '1', '--pretty=tformat:"%ci  %H"']),"utf-8").strip()
  logger.perf("Commit Info: {}".format(commit_info))
except:
  logger.perf("No git info found")
  pass

logger.perf("Start Time: {}".format(start_timestr))
logger.perf("User count: {}   Group count: {}".format(args.count,args.group_count))
logger.perf("Server: {}".format(args.server))
logger.perf("Perf Log file: {}".format(perf_logfile))
if args.stage:
  if args.ldap_stage:
    logger.perf("Creating Stage users via ldap")
  else:
    logger.perf("Creating Stage users via API")
else:
  logger.perf("Creating active users via API")

if args.ldap_group:
  logger.perf("Adding users to groups via LDAP")
  if args.chunk>-1:
    logger.perf("  Using a chunk size of {}".format(args.chunk))
else:
  logger.perf("Adding users to groups via API")

if args.reuse_template:
  logger.perf("Reusing users starting with: '{}'".format(args.reuse_template))
  if args.user_limit>-1:
    logger.perf("  Limiting reuse to first {} users found".format(args.user_limit))

logger.debug(args)
logger.perf('----')
# end start header

client = ClientMeta(args.server,False)
client.login(args.user, args.password)

if args.ldap_group or args.ldap_stage:
  user_dn=client.user_show(args.user,o_all=True)['result']['dn']
  base_user_dn = re.sub("^uid={}".format(args.user),'uid={}',user_dn)
  dom_dn = re.search("(dc=.*)",user_dn, re.IGNORECASE).group(1)
  ldap_server = ldap3.Server(args.server, get_info=ldap3.ALL)
  ldap_conn = ldap3.Connection(ldap_server,user=user_dn, password=args.password, auto_bind=True)

if args.reuse_template:
  user_dn=client.user_show(args.user,o_all=True)['result']['dn']
  base_user_dn = re.sub("^uid={},".format(args.user),'',user_dn)
  logger.debug("base_user_dn: {}".format(base_user_dn))
  ldap_server = ldap3.Server(args.server, get_info=ldap3.ALL)
  ldap_conn = ldap3.Connection(ldap_server,user=user_dn, password=args.password, auto_bind=True)
  users=get_users_ldap(args.reuse_template)
else:  
  logger.info("Creating {} users".format(args.count))
  logger.info("template: {}".format(uid_template))

  logger.info("Checking for existing templated users")
  user_check=client.user_find(uid_template.format(seq=0))
  if user_check["count"]>0:
    sec_to_wait = 61 - datetime.now().second
    logger.error("Existing users found please wait {} seconds".format(sec_to_wait))
    exit(1)
  else:
    logger.info("Proceeding")

  if args.stage:
    users = add_users_stage(args.count)
  else:
    users = add_users_api(args.count)

if args.ldap_group:
  # print(ldap_server.info)

  # for i in iter_timer(range(args.group_count),step=1,label="group_add_user_ldap"):
  #   create_group_add_users_ldap(i,users,ldap_conn,base_user_dn,chunk=args.chunk)

  for i in loop_timer(args.group_count,1,label="group_add_user_ldap"):
    create_group_add_users_ldap(i,users,ldap_conn,base_user_dn,chunk=args.chunk)

elif args.ldap_group_del is not None:
  user_dn=client.user_show(args.user,o_all=True)['result']['dn']
  group_dn=client.group_show(args.ldap_group_del,o_all=True)['result']['dn']
  base_user_dn = re.sub("^uid={}".format(args.user),'uid={}',user_dn)
  ldap_server = ldap3.Server(args.server, get_info=ldap3.ALL)
  ldap_conn = ldap3.Connection(ldap_server,user=user_dn, password=args.password, auto_bind=True)
  remove_group_users_ldap(users, ldap_conn, base_user_dn, args.ldap_group_del, group_dn, chunk=args.chunk)

else:
  for i in loop_timer(args.group_count,1,label="group_add_user_api"):
    create_group_add_users_api(i,users)

logger.perf('----')
logger.perf("End Time: {}".format(datetime.now().strftime("%Y%m%d %H:%M")))
run_time=time.time() - start_time
logger.perf("Total Run Time: {:.3f}sec".format(run_time))
logger.perf("Total Run time: {:d}min {:.3f}sec".format(int(run_time//60),run_time%60))
