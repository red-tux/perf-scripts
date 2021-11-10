Filters for ds-logpipe.py

filter_audit_log.py  - script for filtering audit logs
enable_filter_log.sh - script to enable audit logging to a pipe
disable_filter_log.sh - script to disable audit logging

To run, use the following order of operations, you will need two terminals open, referred to herein as T1 and T2 in the prompt shown

Start the named pipe logger.  This will pass two parameters to the logging plugin, the output file (audit_out) and the DN to use as a base filter (everything under that DN is returned)
T1 $ ./run_filter_log.sh filter_audit_log.py audit_out "idnsname=example.com.,cn=dns,dc=example,dc=com"

Enable the named pipe
T2 $ ./enable_filter_log.sh


When finished:
T2 $ ./disable_filter_log.sh

You may now stop the filter on Terminal 1

If at any time the directory server appears to be hung you may need to "cat" the named pipe multiple times to clear it.


Sample output from running the filter:
[root@ipaserver0 RHDS]# ./run_filter_log.sh filter_audit_log.py audit_out "idnsname=example.com.,cn=dns,dc=example,dc=com"
Starting ds-logpie.py
OPTIONS:  filter_audit_log.logfile=audit_out filter_audit_log.basedn=idnsname=example.com.,cn=dns,dc=example,dc=com

Matched DN: 20211110191928   16 idnsname=test_record,idnsname=example.com.,cn=dns,dc=example,dc=com
 Unmatched: 20211110191928   16 idnsname=example.com.,cn=dns,dc=example,dc=com
Matched DN: 20211110192107   15 idnsname=test_record,idnsname=example.com.,cn=dns,dc=example,dc=com
 Unmatched: 20211110192107   16 idnsname=example.com.,cn=dns,dc=example,dc=com
Discarding entry, no dn or time value found
 Unmatched: 20211110192420   25 cn=config
Discarding entry, no dn or time value found
 Unmatched: 20211110192455   25 cn=config
 Unmatched: 20211110192827   28 cn=MasterCRL,ou=crlIssuingPoints, ou=ca, o=ipaca


Sample output from the log file
[root@ipaserver0 RHDS]# cat audit_out 
time: 20211110193353
dn: idnsname=test_record,idnsname=example.com.,cn=dns,dc=example,dc=com
result: 0
changetype: modify
replace: tXTRecord
tXTRecord: fdsafds
-
replace: modifiersname
modifiersname: uid=admin,cn=users,cn=accounts,dc=example,dc=com
-
replace: modifytimestamp
modifytimestamp: 20211110193353Z
-
replace: entryusn
entryusn: 964866
-

