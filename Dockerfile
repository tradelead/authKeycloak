FROM jboss/keycloak:6.0.1

COPY ./theme /opt/jboss/keycloak/themes/tradelead
COPY ./tradelead-realm.json /tmp/tradelead-realm.json

RUN ./keycloak/bin/kcadm.sh config credentials --server http://localhost:8080/auth --realm master --user $KEYCLOAK_USER --password $KEYCLOAK_PASSWORD
RUN ./keycloak/bin/kcadm.sh update realms/tradelead -s "loginTheme=tradelead"
RUN ./keycloak/bin/kcadm.sh update realms/tradelead -s "accountTheme=tradelead"
RUN ./keycloak/bin/kcadm.sh update realms/tradelead -s "emailTheme=tradelead"
