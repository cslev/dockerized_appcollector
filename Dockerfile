 #this is Debian_12 (Bookworm) - pinned for stability
FROM python:3.11-slim-bookworm
LABEL maintainer="cslev <cslev@gmx.com>"

ENV DEPS="bash \
          nano \
          git \
          curl \
          wget"
           
SHELL ["/bin/bash", "-c"]



RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $DEPS 
    # sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    # locale-gen && \
    # update-locale LANG=en_US.UTF-8

#we copy the requirements first only to avoid installing them every time we modify our code and rebuild the container
COPY src/requirements.txt /appcollector/
WORKDIR /appcollector

RUN pip install --upgrade pip && \
    # Install the requirements
    # --no-cache-dir is used to avoid caching the packages, which saves space
    pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium && \
    #playwright install-deps chromium  && \
    #pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128 && \
    apt-get autoremove --purge -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/pip /tmp/* 

COPY src /appcollector/    
    
# Set up VNC password, add proper permission start script
RUN mv root_bashrc /root/.bashrc && \
#     mkdir -p ~/.vnc && \
#     x11vnc -storepasswd 1234 ~/.vnc/passwd && \
#     chmod +x start_vnc.sh
# # Set the DISPLAY environment variable
# ENV DISPLAY=:1

# We run VNC server but not wts itself
# ENTRYPOINT ["./start_vnc.sh"]