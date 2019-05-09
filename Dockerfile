FROM jboss/keycloak:6.0.1

COPY ./theme /opt/jboss/keycloak/themes/tradelead

COPY ./realm.json /tmp/realm.json
ENV KEYCLOAK_IMPORT=/tmp/realm.json