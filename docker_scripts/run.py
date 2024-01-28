#!/usr/bin/env python3
import os
import shutil
from sys import stdout
import schedule
import subprocess
import time
import tempfile
import errno
from tool_scripts import jellyfin_import
from tool_scripts import spotify_update_playlist
from tool_scripts import tsar


def main():

    def get_envar(envar):
        val = os.environ[envar]
        if val == "":
            raise ValueError(f"envar may not be empty")
        return val

    def verify_writable(path):
        try:
            testfile = tempfile.TemporaryFile(dir = path)
            testfile.close()
        except OSError as ex:
            msg = f"{path} must be accessible and writable"
            msg = '{}: {}'.format(msg, ex.args[0]) if ex.args else str(msg)
            ex.args = (msg,) + ex.args[1:]
            raise


    # check all the env vars
    spotipy_client_id = get_envar("SPOTIPY_CLIENT_ID")
    spotipy_client_secret = get_envar("SPOTIPY_CLIENT_SECRET")
    spotipy_redirect_uri = get_envar("SPOTIPY_REDIRECT_URI")
    spotify_username = get_envar("SPOTIFY_USERNAME")
    spotify_password = get_envar("SPOTIFY_PASSWORD")
    spotify_playlist_uri = get_envar("SPOTIFY_PLAYLIST_URI")
    jellyfin_username = get_envar("JELLYFIN_USERNAME")
    jellyfin_password = get_envar("JELLYFIN_PASSWORD")
    jellyfin_server = get_envar("JELLYFIN_SERVER")
    schedule_frequency = get_envar("SCHEDULE_FREQUENCY")

    # ensure we have the required directories
    jellyfin_library_dir = "/jellyfin"
    temp_import_dir = "/import"
    if not os.path.isdir(temp_import_dir):
        raise ValueError(f"import directory does not exist: {temp_import_dir}")
    if not os.path.isdir(jellyfin_library_dir):
        raise ValueError(f"jellyfin library directory does not exist: {jellyfin_library_dir}")

    # ensure we have the required spotipy api cache
    spotipy_cache = f"/.cache-{spotify_username}"
    if not os.path.isfile(spotipy_cache):
        raise ValueError(f"spotipy authentication cache file is not avilable at: {spotipy_cache}")

    # check required all permissions
    verify_writable(jellyfin_library_dir)
    verify_writable(temp_import_dir)

    def run_update_spotify_playlist():
        print("____ jellyfin-spotify: START updating spotify playlist with new songs _____")
        spotify_update_playlist.run(playlist_id=spotify_playlist_uri, username=spotify_username)
        print("____ jellyfin-spotify: FINISHED updating spotify playlist with new songs _____")

    def run_tsar_and_import():
        # update right before we run tsar to ensure we have all of the latest songs
        run_update_spotify_playlist()
        print("____ jellyfin-spotify: START running tsar ____")
        tsar.run(output_dir=temp_import_dir,
                  playlist_id=spotify_playlist_uri,
                  username=spotify_username,
                  password=spotify_password,
                  librespot_binary="/usr/bin/librespot",
                  empty_playlist=True)
        print("____ jellyfin-spotify: FINISHED running tsar ____")

        print("_____ jellyfin-spotify: START importing new songs into jellyfin ____")
        jellyfin_import.run(jellyfin_username=jellyfin_username,
                             jellyfin_password=jellyfin_password,
                             server=jellyfin_server,
                             import_dir=temp_import_dir,
                             jellyfin_library_dir=jellyfin_library_dir,
                             empty_import_dir=True)
        print("_____ jellyfin-spotify: FINISHED importing new songs into jellyfin ____")


    print("____ Running jellyfin-spotify ____")
    print(f"ENVARS: {os.environ}")

    print(f"waiting for scheduled tasks at time {schedule_frequency}...")
    if schedule_frequency == "NOW":
        run_tsar_and_import()

    elif schedule_frequency == "DEBUG":
        run_tsar_and_import()
        time.sleep(99999)

    else:
        # Immediately update the playlist on start, this ensures our token is valid
        run_update_spotify_playlist()
        # in the rare case we would be scheduled to update the playlist again right away
        # ensure enough time has passed so we don't double-add the songs
        time.sleep(3)

        schedule.every().hour.do(run_update_spotify_playlist)
        # run off the our to avoid conflicting with the playlist update task
        schedule.every(1).day.at(schedule_frequency).do(run_tsar_and_import)
        while True:
            schedule.run_pending()
            time.sleep(60)

    print("Exiting jellyfin-spotify")


if __name__ == "__main__":
    main()
