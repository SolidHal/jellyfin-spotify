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

def spotify_time_to_datetime(T_Z_timestring):
    no_z = re.sub('Z', '', T_Z_timestring)
    return datetime.datetime.fromisoformat(no_z).replace(tzinfo=datetime.timezone.utc)

def get_new_saved_tracks(spotify_api, timestamp):
    """return a list of uris for spotify tracks saved after param:timestamp"""
    new_tracks = []
    track_limit = 50
    offset = 0

    print(f"finding all tracks since {timestamp}")

    def get_tracks():
        num_saved = 0
        saved_tracks = spotify_api.current_user_saved_tracks(limit=track_limit, offset=offset)
        for track in saved_tracks.get("items"):
            if spotify_time_to_datetime(track.get('added_at')) > timestamp:
                print(f"found {track.get('track').get('name')} at {track.get('added_at')}")
                new_tracks.append(track.get('track').get('uri'))
                num_saved +=1

        return num_saved == track_limit

    next = get_tracks()
    offset +=track_limit
    # if every track from the last api request matched our filter, request and check the next set
    while(next):
        next = get_tracks()
        offset += track_limit

    print(f"found {len(new_tracks)} new tracks")

    return new_tracks

def time_now():
    return datetime.datetime.now(datetime.timezone.utc)

def set_playlist_timestamp(spotify_api, playlist_id):
    timestamp = time_now()
    print(f"setting the playlists description to the current datetime: {timestamp}")
    spotify_api.playlist_change_details(playlist_id, description=f"{timestamp}")
    return timestamp

def get_playlist_timestamp(spotify_api, playlist_id):
    """We keep the last time we checked for new saved songs in the description of the destination playlist"""
    playlist = spotify_api.playlist(playlist_id)
    # initialize the playlist description timestamp if it isn't set
    if playlist.get("description") == "":
        print(f"playlist f{playlist_id} does not have a timestamp in its description")
        return set_playlist_timestamp(spotify_api, playlist_id)

    return spotify_time_to_datetime(playlist.get("description"))



def run(playlist_id, username):
    spotify_api = start_api(username)
    timestamp = get_playlist_timestamp(spotify_api, playlist_id)
    new_tracks = get_new_saved_tracks(spotify_api, timestamp)
    if new_tracks:
        spotify_api.playlist_add_items(playlist_id, new_tracks)

    set_playlist_timestamp(spotify_api, playlist_id)



@click.command()
@click.option("--playlist_id", type=str, required=True, help="playlist uri to record, of the form spotify:playlist:<rand>")
@click.option("--username", type=str, required=True, help="username of the user to login as")
def main(playlist_id, username):
    run(playlist_id=playlist_id, username=username)

if __name__ == "__main__":
    main()
