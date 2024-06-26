#!/usr/bin/env python3
import datetime
import os
import sys
import json
import spotipy
import spotipy.util as util
import re
import click
import subprocess
from json.decoder import JSONDecodeError


def start_api(username):
    """
    the following must be set:
    SPOTIPY_CLIENT_ID
    SPOTIPY_CLIENT_SECRET
    SPOTIPY_REDIRECT_URI
    """
    # check for env vars
    os.environ["SPOTIPY_CLIENT_ID"]
    os.environ["SPOTIPY_CLIENT_SECRET"]
    os.environ["SPOTIPY_REDIRECT_URI"]
    scope = 'user-read-private user-read-playback-state user-modify-playback-state user-library-read playlist-modify-private playlist-modify-public'

    try:
        token = util.prompt_for_user_token(username, scope)
    except (AttributeError, JSONDecodeError):
        os.remove(f".cache-{username}")
        token = util.prompt_for_user_token(username, scope)

    spotify_api = spotipy.Spotify(auth=token, retries=10, status_retries=10, backoff_factor=1.5)

    return spotify_api


def run(username):
    spotify_api = start_api(username)
    if spotify_api.tracks(["https://open.spotify.com/track/5goZCkRmpk5tWTX3Af6XRL?si=7d1fe0c9ea4b4ff4"]) is None:
        raise RuntimeError("unable to retrieve track information, is the cache file valid?")

@click.command()
@click.option("--username", type=str, required=True, help="username of the user to login as")
def main(username):
    run(username=username)

if __name__ == "__main__":
    main()