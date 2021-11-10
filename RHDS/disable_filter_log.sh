#!/bin/bash

# Set these variables as needed
INSTANCE=$(hostname -d | tr [a-z] [A-Z] | tr . -)

# The acocunt to use to perform the ldap modify operation
LDAP_MOD_ACT="cn=Directory Manager"


echo "Please enter the password for the LDAP user: '$LDAP_MOD_ACT'"

stty -echo
read -p "Password: " PASSOWRD
stty echo
echo

echo "Enabeling auditlog"
cat << 'EOF' | ldapmodify -D "$LDAP_MOD_ACT" -w "$PASSWORD"
replace: nsslapd-auditlog-logging-enabled
nsslapd-auditlog-logging-enabled: off
EOF
echo "done"
