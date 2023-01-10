#!/usr/bin/env python3
import airsonic_import
from airsonic_import import Song as Song
import click
import os

@click.command()
@click.option("--airsonic_username", type=str, required=True, help="username of the user to login as")
@click.option("--airsonic_password", type=str, required=True, help="password of the user to login as")
@click.option("--server", type=str, required=True, help="server url")
@click.option("--port", type=str, required=True, help="server port")
@click.option("--song_name_artist", "-S", type=str, multiple=True, required=True, help="a song to add to the playlist")
def main(airsonic_username, airsonic_password, server, port, song_name_artist):

    if len(song_name_artist) == 0:
        return

    # create the songs entries
    songs=[]
    for entry in song_name_artist:
        artist = entry.split("-")[0]
        name = entry.split("-")[1]
        song = Song(name=name, artist=artist, album="", original_file="", airsonic_library_file=name)
        songs.append(song)


    airsonic_api = airsonic_import.connect_airsonic(server, port, airsonic_username, airsonic_password)
    playlist_id = airsonic_import.get_create_playlist(airsonic_api)
    airsonic_import.get_airsonic_song_ids(airsonic_api, songs)
    airsonic_import.update_playlist(airsonic_api, playlist_id, songs)

if __name__ == "__main__":
    main()
