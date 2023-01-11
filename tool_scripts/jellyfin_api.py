#!/usr/bin/env python3

import requests
import time


# Set required authorization header
headers = {}
authorization = (
    'MediaBrowser , '
    'Client="other", '
    'Device="script", '
    'DeviceId="script", '
    'Version="0.0.0"'
)
headers['x-emby-authorization'] = authorization


class jellyfin:

    def __init__(self, server_url, username, password):
        self.server_url = server_url
        self.headers = headers
        # Build json payload to authenticate to the server
        auth_data = {
            'Username': username,
            'Pw': password
        }
        r = requests.post(f'{self.server_url}/Users/AuthenticateByName', headers=self.headers, json=auth_data)
        r.raise_for_status()

        token = r.json().get('AccessToken')
        self.user_id = r.json().get('User').get('Id')
        # Include the auth token in headers
        self.headers['x-mediabrowser-token'] = token
        print(f"Authenticated to {server_url} as user {username}")


    ## Basic
    def get(self, endpoint, parameters=None):
        r = requests.get(f'{self.server_url}/{endpoint}', headers=self.headers, params=parameters)
        r.raise_for_status()
        return r.json()

    def post(self, endpoint, body=None, parameters=None):
        r = requests.post(f'{self.server_url}/{endpoint}', headers=self.headers, json=body, params=parameters)
        r.raise_for_status()
        if 'application/json' in r.headers.get('Content-Type', ''):
            return r.json()

    ## Specific
    def lookup_playlist_id(self, playlist_name):
        # example of how to handle query parameters
        parameters = {"searchTerm" : playlist_name, "includeItemTypes" : "Playlist", "mediaTypes": "Audio"}
        endpoint = "Search/Hints"
        res = self.get(endpoint, parameters)["SearchHints"]
        for playlist in res:
            if playlist["Name"] == playlist_name:
                return playlist["ItemId"]

    def lookup_playlist_items(self, playlist_id):
        endpoint = f"Playlists/{playlist_id}/Items"
        parameters = {"userId" : self.user_id}
        return self.get(endpoint, parameters)

    def create_playlist(self, playlist_name):
        body = {"name": playlist_name, "ids": [], "userID": self.user_id, "MediaType": None}
        endpoint = "Playlists"
        return self.post(endpoint, body=body)["Id"]

    def add_playlist_items(self, playlist_id, item_ids):
        endpoint = f"Playlists/{playlist_id}/Items"
        parameters = {"ids": item_ids}
        return self.post(endpoint, parameters=parameters)

    def lookup_song(self, song_name, artist_name):
        parameters = {"searchTerm" : f"{song_name}", "includeItemTypes" : "Audio"}
        endpoint = "Search/Hints"
        res = self.get(endpoint, parameters)["SearchHints"]
        for song in res:
            if (song["AlbumArtist"] == artist_name or artist_name in song["Artists"]):
                return song

        print("unable to find song matching name: {name}, artist: {artist_name}")
        return None

    def item_file_path(self, item_id):
        endpoint = f"Items/{item_id}/PlaybackInfo"
        parameters = {"userId" : self.user_id}
        r = self.get(endpoint, parameters)
        return r["MediaSources"][0]["Path"]

    def scan_library_status(self):
        endpoint = "ScheduledTasks"
        r = self.get(endpoint)
        for task in r:
            if task["Key"] == "RefreshLibrary":
                return task
        return None

    def scan_library(self):
        # start
        endpoint = "Library/Refresh"
        self.post(endpoint)

        def scanning():
            state = self.scan_library_status()["State"]
            if state == "Idle":
                return False
            return True

        # busy loop on state
        time.sleep(2)
        while(scanning()):
            print("scanning...")
            time.sleep(10)


        print("library scan complete")




def main():
    jelly = jellyfin(server_url, username, password)

    # r = jelly.lookup_playlist("test")
    # print(r)

    # r = jelly.lookup_song("mememe", "100 gecs")
    # print(r)

#     r = jelly.get("ScheduledTasks")
#     '''
# {'StartTimeUtc': '2023-01-10T15:59:55.9646922Z', 'EndTimeUtc': '2023-01-10T16:01:32.6057085Z', 'Status': 'Completed', 'Name': 'Scan Media Library', 'Key': 'RefreshLibrary', 'Id': '7738148ffcd07979c7ceb148e06b3aed'}, 'Triggers': [{'Type': 'IntervalTrigger', 'IntervalTicks': 432000000000}], 'Description': 'Scans your media library for new files and refreshes metadata.', 'Category': 'Library', 'IsHidden': False, 'Key': 'RefreshLibrary'}
#     '''
#     print(r)

    # jelly.scan_library()

    # r = jelly.item_file_path("16e0afb01cfb51b4481e538f868a195e")
    # print(r)

    # r = jelly.lookup_playlist_id("test")
    # print(r)
    # r = jelly.lookup_playlist_items(r)
    # print(r)

    # r = jelly.lookup_song("home", "Cavetown")
    # print(r)
    # song_id1 = r["ItemId"]

    # r = jelly.lookup_song("Blueberry", "Manatee Commune")
    # print(r)
    # song_id2 = r["ItemId"]
    # r = jelly.create_playlist("test8")
    # print(r)

    # jelly.add_playlist_items("e7de5fc9f02e736436aa0a2b882f874b", [song_id1, song_id2])
    # r = jelly.lookup_playlist_items("e7de5fc9f02e736436aa0a2b882f874b")
    # print(r)





if __name__ == "__main__":
    main()
