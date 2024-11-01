#!/usr/bin/env python3
from . import jellyfin_api
import datetime
import time
import click
import eyed3
import os
import re
import shutil


def remove_file(filename):
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass

def sanitize_filename(filename):
    """Takes only a filename, not a full path"""
    return re.sub('/', ' ', filename).strip()

class Song:
    def __init__(self, name, artist, album, original_file, jellyfin_library_file):
        self._name = name
        self._artist  = artist
        self._album = album
        self._original_file = original_file
        self._jellyfin_library_file = jellyfin_library_file
        self._jellyfin_song_id = None

    @property
    def name(self):
        return self._name
    @property
    def artist(self):
        return self._artist

    @property
    def album(self):
        return self._album

    @property
    def original_file(self):
        return self._original_file

    @property
    def jellyfin_library_file(self):
        return self._jellyfin_library_file

    @property
    def jellyfin_song_id(self):
        return self._jellyfin_song_id

    @jellyfin_song_id.setter
    def jellyfin_song_id(self, value):
        self._jellyfin_song_id = value

    def __str__(self):
        return f"name: {self._name}, artist: {self._artist}, album: {self._album}, library_file: {self._jellyfin_library_file}, original_file: {self._original_file}, jellyfin_song_id: {self._jellyfin_song_id}"



def canonical_artist(audiofile):
    track_artist = sanitize_filename(audiofile.tag.artist.split(";")[0])
    album_artist = sanitize_filename(audiofile.tag.album_artist.split(";")[0])

    if album_artist not in track_artist:
        # if the album artist is generic, just use the track artist
        if "Various Artists" in album_artist:
            return track_artist
        elif "Various Artists" in track_artist:
            return album_artist
        elif "Traditional" in album_artist:
            return track_artist
        elif "Traditional" in track_artist:
            return album_artist
        # if we get here and we have not found an appropriate artist, default to the track artist
        # track artist is generally the correct artist
        print(f"picking track artist as canonical artist, track_artist = {track_artist}, album_artist = {album_artist}")
        return track_artist

    return track_artist


def import_songs_jellyfin(import_dir, jellyfin_library_dir):
    _, _, song_files = next(os.walk(import_dir), (None, None, []))

    songs = []

    print(f"importing {len(song_files)} songs...")

    for song_file in song_files:
        audiofile = eyed3.load(f"{import_dir}/{song_file}")

        # multiple artists will look like artist1;artist2;artist3
        artist_dir = canonical_artist(audiofile)
        album_dir = sanitize_filename(audiofile.tag.album)
        song_dir = f"{jellyfin_library_dir}/{artist_dir}/{album_dir}"
        os.makedirs(song_dir, exist_ok=True)
        shutil.copy2(f"{import_dir}/{song_file}", song_dir)

        #TODO which provides better jellyfin search results, straight id3 tags or sanitized canonical versions?
        # id3 tags seems to be good
        song = Song(name=audiofile.tag.title,
                    artist=artist_dir,
                    album=album_dir,
                    original_file=f"{import_dir}/{song_file}",
                    jellyfin_library_file=f"{song_dir}/{song_file}")

        songs.append(song)

    return songs


def get_jellyfin_song_id(jelly, song):
    def sanitize_string(in_string):
        return in_string.lower().lstrip(" ").rstrip("")

    # jellyfin search chokes hard on single quotes
    # there doesn't seem to be a way to escape them
    # additionally, search results are not handled properly:
    # searching for a song named "Jack's Song" will not return a song titled "Jack's Song" when it should
    # searching for "Jacks Song" will not return a song titled "Jacks's Song" when it should
    # searching for "Jack" or "s Song" will return a song titled "Jack's Song" so lets search based on the longest string
    # we can search by

    lookup_song_name = song.name
    if "'" in song.name:
        print(f"single quote found in song name {song.name} picking a lookup_song_name")
        lookup_song_name = ""
        parts = song.name.split("'")
        for part in parts:
            if len(part) > len(lookup_song_name):
                lookup_song_name = part
    if '"' in song.name:
        print(f"double quote found in song name {song.name} picking a lookup_song_name")
        lookup_song_name = ""
        parts = song.name.split('"')
        for part in parts:
            if len(part) > len(lookup_song_name):
                lookup_song_name = part
    if "—" in song.name:
        print(f"long dash found in song name {song.name} picking a lookup_song_name")
        lookup_song_name = ""
        parts = song.name.split("—")
        for part in parts:
            if len(part) > len(lookup_song_name):
                lookup_song_name = part

    lookup_song_artist = song.artist
    if "'" in song.artist:
        print(f"single quote found in artist name {song.artist} picking a lookup_song_artist")
        lookup_song_artist = ""
        parts = song.artist.split("'")
        for part in parts:
            if len(part) > len(lookup_song_artist):
                lookup_song_artist = part
    if '"' in song.artist:
        print(f"double quote found in artist name {song.artist} picking a lookup_song_artist")
        lookup_song_artist = ""
        parts = song.artist.split('"')
        for part in parts:
            if len(part) > len(lookup_song_artist):
                lookup_song_artist = part
    if "—" in song.artist:
        print(f"long dash found in artist name {song.artist} picking a lookup_song_artist")
        lookup_song_artist = ""
        parts = song.artist.split("—")
        for part in parts:
            if len(part) > len(lookup_song_artist):
                lookup_song_artist = part


    print(f"Looking for song {song.name} {song.artist} using {lookup_song_name} {lookup_song_artist}")
    r = jelly.lookup_song(lookup_song_name, lookup_song_artist)
    if r is None:
        print(f"no results when searching with {lookup_song_name} {lookup_song_artist}. Trying just: {lookup_song_name}")
        r = jelly.lookup_song(lookup_song_name, "")



    if r is not None:
        item_id = r["ItemId"]
        res_path = jelly.item_file_path(item_id)
        res_path = sanitize_string(res_path)
        lib_file = sanitize_string(song.jellyfin_library_file.split("/")[-1])
        print(f"Finding song id: Checking if {lib_file} is in {res_path}")
        if lib_file in res_path:
            print(f"Found song       name:  {r.get('Name')}, artists: {r.get('Artists')}, album: {r.get('Album')}, library_file: {res_path}, id: {item_id}")
            song.jellyfin_song_id = item_id
            return

    raise ValueError(f"""unable to find song in jellyfin search results. None of the results matched the following:
    library_file = {sanitize_string(song.jellyfin_library_file)}
    ==================================================================
    song = {song}
    ==================================================================
    """)


def get_create_playlist(jelly, name):
    playlist_id = jelly.lookup_playlist_id(name)
    if playlist_id:
        playlist_items = jelly.lookup_playlist_items(playlist_id)
        print(f"found playlist name = {name}, id = {playlist_id}, songCount = {playlist_items.get('TotalRecordCount')}")
        return playlist_id

    # not found, lets make it
    print(f"creating playlist with name {name}")
    created_playlist_id = jelly.create_playlist(name)
    playlist_id = jelly.lookup_playlist_id(name)
    if created_playlist_id != playlist_id:
        raise ValueError("Unable to find the playlist after creating it, name: {name}, id: {created_playlist_id}")

    return playlist_id

def update_playlist(jelly, playlist_id, songs):
    curr_size = jelly.lookup_playlist_items(playlist_id).get('TotalRecordCount')

    new_ids = []
    for song in songs:
        # skip over songs without a jellyfin song id
        if song.jellyfin_song_id:
            new_ids.append(song.jellyfin_song_id)
        else:
            print(f"skipping song {song.name} as it is missing a jellyfin song id")
    jelly.add_playlist_items(playlist_id, new_ids)
    expected_size = curr_size + len(new_ids)

    actual_size = jelly.lookup_playlist_items(playlist_id).get('TotalRecordCount')

    if(expected_size != actual_size):
        raise ValueError(f"expected {expected_size} songs in playlist after adding {len(new_ids)} songs. Found {actual_size} songs in playlist.")
    print(f"Added {len(new_ids)} songs to playlist {playlist_id}")


def run(jellyfin_username, jellyfin_password, server, import_dir, jellyfin_library_dir, empty_import_dir):
    if not os.path.isdir(import_dir):
        raise ValueError(f"import directory does not exist: {import_dir}")
    if not os.path.isdir(jellyfin_library_dir):
        raise ValueError(f"jellyfin library directory does not exist: {jellyfin_library_dir}")

    failed_lookups = []

    jelly = jellyfin_api.jellyfin(server, jellyfin_username, jellyfin_password)
    songs = import_songs_jellyfin(import_dir, jellyfin_library_dir)
    jelly.scan_library()
    for song in songs:
        try:
            get_jellyfin_song_id(jelly, song)
        except ValueError as e:
            print("Failed to find song in jellyfin, continuing")
            # hold the error until later so we can try to do our best creating and filling the playlist
            failed_lookups.append(e)

    date = datetime.datetime.now()
    playlist_name = date.strftime("%Y") + " " + date.strftime("%m") + " " + date.strftime("%B")
    playlist_id = get_create_playlist(jelly, playlist_name)
    update_playlist(jelly, playlist_id, songs)

    if failed_lookups:
        # if we failed some lookups, 
        print("Failed the following lookups:")
        for failed_lookup in failed_lookups:
            print(failed_lookup)
        raise ValueError("Failed to add all songs to playlist")

    if empty_import_dir:
        for song in songs:
            os.remove(song.original_file)


def run_manual(jellyfin_username, jellyfin_password, server, import_dir, jellyfin_library_dir, empty_import_dir, playlist_name):
    if not os.path.isdir(import_dir):
        raise ValueError(f"import directory does not exist: {import_dir}")
    if not os.path.isdir(jellyfin_library_dir):
        raise ValueError(f"jellyfin library directory does not exist: {jellyfin_library_dir}")

    jelly = jellyfin_api.jellyfin(server, jellyfin_username, jellyfin_password)
    songs = import_songs_jellyfin(import_dir, jellyfin_library_dir)
    jelly.scan_library()

    if playlist_name is not None:
        print(f"creating new playlist {playlist_name}")
        for song in songs:
            get_jellyfin_song_id(jelly, song)
        playlist_id = get_create_playlist(jelly, playlist_name)
        update_playlist(jelly, playlist_id, songs)

    if empty_import_dir:
        for song in songs:
            os.remove(song.original_file)

@click.command()
@click.option("--jellyfin_username", type=str, required=True, help="username of the user to login as")
@click.option("--jellyfin_password", type=str, required=True, help="password of the user to login as")
@click.option("--server", type=str, required=True, help="server url")
@click.option("--import_dir", type=str, required=True, help="directory to import music from")
@click.option("--jellyfin_library_dir", type=str, required=True, help="directory to import music to")
@click.option("--empty_import_dir", is_flag=True, default=False, help="remove all songs from the import_dir when complete")
def main(jellyfin_username, jellyfin_password, server, import_dir, jellyfin_library_dir, empty_import_dir):
    run(jellyfin_username=jellyfin_username,
        jellyfin_password=jellyfin_password,
        server=server,
        import_dir=import_dir,
        jellyfin_library_dir=jellyfin_library_dir,
        empty_import_dir=empty_import_dir)

if __name__ == "__main__":
    main()
