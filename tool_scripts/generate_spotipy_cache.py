#!/usr/bin/env python3
import spotify_update_playlist
import click
import os

@click.command()
@click.option("--username", type=str, required=True, help="username of the user to login as")
def main(username):
    """
    the following must be set:
    SPOTIPY_CLIENT_ID
    SPOTIPY_CLIENT_SECRET
    SPOTIPY_REDIRECT_URI
    """
    spotify_api = spotify_update_playlist.start_api(username)
    print(f"Created spotipy credental cache file at .cache-{username}")


if __name__ == "__main__":
    main()
