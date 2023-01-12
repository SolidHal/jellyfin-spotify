#!/usr/bin/bash

if [[ -z "$PUID" ]]; then
    echo "PUID envar must be set"
    exit
fi

if [[ -z "$PGID" ]]; then
    echo "PGID envar must be set"
    exit
fi

PUID=${PUID:-911}
PGID=${PGID:-911}

groupmod -o -g "$PGID" abc
usermod -o -u "$PUID" abc

echo '
-------------------------------------
GID/UID
-------------------------------------'
echo "
User uid:    $(id -u abc)
User gid:    $(id -g abc)
-------------------------------------
"

# update tsar
git -C /tsar pull

# create our working dir
mkdir -p /import

# take ownership of our working directories and files
chown abc:abc /import
chown abc:abc /.cache-*
chown abc:abc /jellyfin

# run the actual script with proper permissions
su abc -s /run.py
