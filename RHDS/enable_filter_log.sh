#!/bin/bash

# Set these variables as needed
INSTANCE=$(hostname -d | tr [a-z] [A-Z] | tr . -)

# The acocunt to use to perform the ldap modify operation
LDAP_MOD_ACT="cn=Directory Manager"


echo "Please enter the password for the LDAP user: '$LDAP_MOD_ACT'"

stty -echo
read -p "Password: " PASSWORD
stty echo
echo

echo "Enabeling auditlog"
ldapmodify -D "$LDAP_MOD_ACT" -w "$PASSWORD" <<EOF
dn: cn=config
changetype: modify
replace: nsslapd-auditlog
nsslapd-auditlog: /var/log/dirsrv/slapd-$INSTANCE/audit.pipe
-
replace: nsslapd-auditlog-maxlogsperdir
nsslapd-auditlog-maxlogsperdir: 1
-
replace: nsslapd-auditlog-logexpirationtime
nsslapd-auditlog-logexpirationtime: -1
-
replace: nsslapd-auditlog-logrotationtime
nsslapd-auditlog-logrotationtime: -1
-
replace: nsslapd-auditlog-logging-enabled
nsslapd-auditlog-logging-enabled: on
EOF
echo "done"
