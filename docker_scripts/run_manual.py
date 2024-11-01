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
from tool_scripts import spotify_get_playlist_name
from tool_scripts import validate_spotify_cache
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
    jellyfin_username = get_envar("JELLYFIN_USERNAME")
    jellyfin_password = get_envar("JELLYFIN_PASSWORD")
    jellyfin_server = get_envar("JELLYFIN_SERVER")


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

    # ensure we have the required librespot api cache
    librespot_cache_dir = f"/librespot_cache_dir"
    librespot_credentials_json = f"/librespot_cache_dir/credentials.json"
    if not os.path.isfile(librespot_credentials_json):
        raise ValueError(f"librespot credentials cache file is not avilable at: {librespot_credentials_json}")

    # check required all permissions
    verify_writable(jellyfin_library_dir)
    verify_writable(temp_import_dir)

    # ensure our cache file works
    validate_spotify_cache.run(username=spotify_username)

    def run_tsar_and_import(uri):

        if "playlist" in uri:
            playlist_name = spotify_get_playlist_name.run(username=spotify_username,
                                                          playlist_id=uri)
        else:
            playlist_name = None

        print(f"____ jellyfin-spotify: START running tsar for uri {uri} ____")
        tsar.run(output_dir=temp_import_dir,
                  uri=uri,
                  cache_dir=librespot_cache_dir,
                  username=spotify_username,
                  librespot_binary="/usr/bin/librespot",
                  empty_playlist=False)
        print(f"____ jellyfin-spotify: FINISHED running tsar for uri {uri} ____")

        print(f"_____ jellyfin-spotify: START importing new songs into jellyfin  for uri {uri}  ____")
        jellyfin_import.run_manual(jellyfin_username=jellyfin_username,
                             jellyfin_password=jellyfin_password,
                             server=jellyfin_server,
                             import_dir=temp_import_dir,
                             jellyfin_library_dir=jellyfin_library_dir,
                             empty_import_dir=True,
                             playlist_name=playlist_name)
        print(f"_____ jellyfin-spotify: FINISHED importing new songs into jellyfin  for uri {uri} ____")


    print("____ Running jellyfin-spotify manual____")
    print(f"ENVARS: {os.environ}")

    # spotify links file is one link per line
    with open("/spotify_links.txt") as spotify_links_file:
        links = spotify_links_file.readlines()

    unimported_links = links

    for link in links:
        run_tsar_and_import(link)

        # remove the link from the file now that we have successfully imported it
        unimported_links.remove(link)

        open("/spotify_links.txt", "w").close()
        with open("/spotify_links.txt", "r+") as spotify_links_file:
            for unimported_link in unimported_links:
                spotify_links_file.write(unimported_link)



    print("Exiting jellyfin-spotify manual")


if __name__ == "__main__":
    main()