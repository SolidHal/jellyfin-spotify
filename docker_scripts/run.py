#!/usr/bin/env python3
import os
import shutil
from sys import stdout
import schedule
import subprocess
import time
import tempfile
import errno
from tool_scripts import airsonic_import
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
    airsonic_username = get_envar("AIRSONIC_USERNAME")
    airsonic_password = get_envar("AIRSONIC_PASSWORD")
    airsonic_server = get_envar("AIRSONIC_SERVER")
    airsonic_port = get_envar("AIRSONIC_PORT")
    schedule_frequency = get_envar("SCHEDULE_FREQUENCY")

    # ensure we have the required directories
    airsonic_library_dir = "/airsonic"
    temp_import_dir = "/import"
    if not os.path.isdir(temp_import_dir):
        raise ValueError(f"import directory does not exist: {temp_import_dir}")
    if not os.path.isdir(airsonic_library_dir):
        raise ValueError(f"airsonic library directory does not exist: {airsonic_library_dir}")

    # ensure we have the required spotipy api cache
    spotipy_cache = f"/.cache-{spotify_username}"
    if not os.path.isfile(spotipy_cache):
        raise ValueError(f"spotipy authentication cache file is not avilable at: {spotipy_cache}")

    # check required all permissions
    verify_writable(airsonic_library_dir)
    verify_writable(temp_import_dir)

    def run_update_spotify_playlist():
        print("____ airsonic-spotify: START updating spotify playlist with new songs _____")
        # TODO will this run in the root dir? if not then the cache token won't be available
        # spotipy envars are provided by the caller
        spotify_update_playlist.run(playlist_id=spotify_playlist_uri, username=spotify_username)
        print("____ airsonic-spotify: FINISHED updating spotify playlist with new songs _____")

    def run_tsar_and_import():
        run_update_spotify_playlist()
        print("____ airsonic-spotify: START running tsar ____")
        tsar.run(output_dir=temp_import_dir,
                  playlist_id=spotify_playlist_uri,
                  username=spotify_username,
                  password=spotify_password,
                  librespot_binary="/usr/bin/librespot",
                  empty_playlist=True)
        print("____ airsonic-spotify: FINISHED running tsar ____")

        print("_____ airsonic-spotify: START importing new songs into airsonic ____")
        airsonic_import.run(airsonic_username=airsonic_username,
                             airsonic_password=airsonic_password,
                             server=airsonic_server,
                             port=airsonic_port,
                             import_dir=temp_import_dir,
                             airsonic_library_dir=airsonic_library_dir,
                             empty_import_dir=True)
        print("_____ airsonic-spotify: FINISHED importing new songs into airsonic ____")


    print("____ Running airsonic-spotify ____")
    print(f"ENVARS: {os.environ}")
    print(f"waiting for scheduled tasks at time {schedule_frequency}...")
    if schedule_frequency == "NOW":
        run_tsar_and_import()

    elif schedule_frequency == "DEBUG":
        run_tsar_and_import()
        time.sleep(99999)

    else:
        schedule.every().hour.do(run_update_spotify_playlist)
        # run off the our to avoid conflicting with the playlist update task
        schedule.every(1).day.at(schedule_frequency).do(run_tsar_and_import)
        while True:
            schedule.run_pending()
            time.sleep(60)

    print("Exiting airsonic-spotify")


if __name__ == "__main__":
    main()
