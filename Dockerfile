ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip
COPY rootfs /
RUN pip3 install --no-cache-dir --break-system-packages -r /usr/bin/requirements.txt
RUN chmod +x /etc/services.d/naim-bridge/run
RUN chmod +x /usr/bin/bridge.py
