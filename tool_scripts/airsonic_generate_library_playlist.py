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
def main(airsonic_username, airsonic_password, server, port):

    def get_next_album_list(airsonic_api, offset) -> list:
        reply = airsonic_api.getAlbumList2(ltype="alphabeticalByName",
                                                size=500,
                                                offset=offset)
        new_albums = reply.get("albumList2").get("album", [])
        return new_albums

    def get_song_ids(airsonic_api):
        albums = []
        offset = 0
        new_albums = get_next_album_list(airsonic_api, offset)
        while len(new_albums) != 0:
            albums = albums + new_albums
            offset += 500
            new_albums = get_next_album_list(airsonic_api, offset)


        songs = []
        print(f"found {len(albums)} albums")
        for album in albums:
            reply = airsonic_api.getAlbum(album.get("id"))
            new_songs = reply.get("album").get("song", [])
            for song_entry in new_songs:
                song = Song(name="", artist="", album="", original_file="", airsonic_library_file="")
                song.airsonic_song_id = song_entry.get("id")
                songs.append(song)

        return songs

    airsonic_api = airsonic_import.connect_airsonic(server, port, airsonic_username, airsonic_password)
    name = "ALL_SONGS"
    playlist_id = airsonic_import.get_create_playlist(airsonic_api, name)
    songs = get_song_ids(airsonic_api)

    print(f"found {len(songs)} songs in the library")

    airsonic_import.update_playlist(airsonic_api, playlist_id, songs)

if __name__ == "__main__":
    main()
