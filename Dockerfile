# syntax=docker/dockerfile:1
FROM ubuntu:latest

# the following envars must be set
ENV PUID=""
ENV PGID=""
ENV SPOTIFY_USERNAME=""
ENV SPOTIFY_PASSWORD=""
ENV SPOTIPY_CLIENT_ID=""
ENV SPOTIPY_CLIENT_SECRET=""
ENV SPOTIPY_REDIRECT_URI=""
ENV SPOTIFY_PLAYLIST_URI=""
ENV JELLYFIN_USERNAME=""
ENV JELLYFIN_PASSWORD=""
ENV JELLYFIN_SERVER=""
ENV SCHEDULE_FREQUENCY=""
#one of:
#  - NOW  : Run tsar & update jellyfin playlist immediately, and then exit
#  - <HH:MM> : run tsar & update jellyfin playlist daily at <HH:MM> UTC
#  - DEBUG : Like "NOW" but does not automatically exit when complete

# the following directories must be provided
# JELLYFIN_LIBRARY_DIR mapped to /jellyfin

# the following file must be provided
# spotipy authentication cache file mapped to "/.cache-<spotify_username>"

ENV LANG C.UTF-8
ENV TZ America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Get Ubuntu packages
RUN apt-get update && apt-get install -y  --no-install-recommends \
    curl \
    wget \
    python3 \
    git \
    python3-pip \
    ffmpeg

# Get python packages
RUN pip3 install \
    py-sonic \
    click \
    eyed3 \
    spotipy \
    schedule

# clean up to minimize image size
RUN rm -rf /var/cache/apt/archives && rm -rf /usr/share/doc && rm -rf /usr/share/man

# Get librespot, use prebuilt x86_64 binary to minimize image size
# saves ~2GB of image size, and a ton of time
# TODO switch to upstream librespot once PR has merged
RUN wget https://github.com/SolidHal/librespot/releases/download/vdebug/librespot -O /usr/bin/librespot && chmod +x /usr/bin/librespot

# create the user and group
RUN useradd -u 911 -U -d /config -s /bin/false abc
RUN usermod -G users abc
RUN mkdir -p /config

# Setup script lib folder
RUN mkdir -p /tool_scripts
RUN touch /tool_scripts/__init__.py

# Get tsar
RUN git clone https://github.com/SolidHal/tsar.git /tsar
RUN cd tool_scripts && ln -s /tsar/tsar.py tsar.py

# Get supporting scripts
COPY tool_scripts/jellyfin_api.py /tool_scripts/jellyfin_api.py
COPY tool_scripts/jellyfin_import.py /tool_scripts/jellyfin_import.py
COPY tool_scripts/spotify_update_playlist.py /tool_scripts/spotify_update_playlist.py

# dont buffer python log output
ENV PYTHONUNBUFFERED="TRUE"

COPY docker_scripts/entrypoint.sh /entrypoint.sh
COPY docker_scripts/run.py /run.py
ENTRYPOINT ["/entrypoint.sh"]