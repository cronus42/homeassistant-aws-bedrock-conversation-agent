ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python and pip
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages \
    boto3==1.35.* \
    pyyaml==6.0.* \
    aiohttp==3.10.*

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

# Copy Python application
COPY bedrock_agent.py /

# Labels
LABEL \
    io.hass.name="AWS Bedrock Conversation Agent" \
    io.hass.description="Use Amazon Bedrock LLMs as conversation agents" \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64|armhf|armv7|i386"

CMD [ "/run.sh" ]
