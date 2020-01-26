import spotipy
import spotipy.util as util
from pprint import pprint
import argparse
import os

SCOPE = "user-library-read playlist-read-private user-library-modify playlist-modify-public"
REDIRECT_URI = "http://localhost/"


class SpotifyManager:
    def __init__(self):
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        self._user_name = os.environ.get('SPOTIFY_USERNAME')
        token = util.prompt_for_user_token(self._user_name,
                                           SCOPE,
                                           client_id,
                                           client_secret,
                                           redirect_uri=REDIRECT_URI)
        self._spotify = spotipy.Spotify(auth=token)
        self._dry_run = True
        self._track_ids_to_add = []

    def get_all_playlists(self):
        playlists = self._spotify.user_playlists(self._user_name)
        result = []
        for item in playlists["items"]:
            if item["owner"]["id"] == self._user_name:
                result.append({
                    "owner": item["owner"]["id"],
                    "name": item["name"],
                    "id": item["id"],
                    "total_tracks": item["tracks"]["total"]
                })
        return result

    def get_playlist_tracks(self, playlist_name):
        result = []
        playlist_id = self.get_playlist_id_by_name(playlist_name)
        results = self._spotify.user_playlist_tracks(self._user_name,
                                                     playlist_id)
        tracks = results["items"]
        while results["next"]:
            results = self._spotify.next(results)
            tracks.extend(results["items"])
        for track in tracks:
            result.append({
                "id":
                track["track"]["id"],
                "name":
                track["track"]["name"],
                "album":
                track["track"]["album"]["name"],
                "artists":
                ",".join(
                    [artist["name"] for artist in track["track"]["artists"]])
            })
        return result

    def get_playlist_id_by_name(self, playlist_name):
        playlists = self.get_all_playlists()
        for playlist in playlists:
            if playlist["name"].upper() == playlist_name.upper():
                return playlist["id"]
        raise Exception(f"playlist id {playlist_name} not found!")

    def get_track_info(self, track_id):
        return self._spotify.track(track_id)

    def find_duplicates_in_playlists(self, playlist_a, playlist_b):
        playlist_a_tack_info = self.get_playlist_tracks(playlist_a)
        playlist_b_tack_info = self.get_playlist_tracks(playlist_b)

        playlist_a_track_names = [
            track["name"] for track in playlist_a_tack_info
        ]
        playlist_b_track_names = [
            track["name"] for track in playlist_b_tack_info
        ]

        duplicates = set(playlist_a_track_names).intersection(
            playlist_b_track_names)

        duplicates_info = []
        for item in duplicates:
            for track in playlist_b_tack_info:
                if item == track["name"]:
                    track["playlist_name"] = playlist_b
                    duplicates_info.append(track)

        return duplicates_info

    def add_tracks_to_playlist(self, tracks, playlist_name):
        playlist_tracks = self.get_playlist_tracks(playlist_name)
        playlist_id = self.get_playlist_id_by_name(playlist_name)
        missed = 0
        tracks_to_add = []
        for track in tracks:
            if self._is_track_in_playlist(playlist_tracks, track["name"],
                                          track["artists"]):
                print(
                    f'Skipping (already exists): {track["name"]} - {track["artists"]}'
                )
                missed = missed + 1
            else:
                track_id = self.search_tracks(track["name"], track["artists"])
                if track_id:
                    tracks_to_add.append(track_id)

        print("already there: ", missed)
        print("found: ", len(list(set(tracks_to_add))))
        pprint(list(set(tracks_to_add)))

        # self._spotify.user_playlist_add_tracks(USER_NAME, playlist_id,
        #                                        tracks_to_add)

    def search_tracks(self, track_name, artist_name):
        result = self._spotify.search(q=f"track:{track_name}",
                                      type='track',
                                      limit=50)
        all_results = result["tracks"]["items"]

        for item in all_results:
            if item["artists"][0]["name"].upper() == artist_name.upper():
                print(
                    f'{item["id"]} - {item["artists"][0]["name"]} - {item["name"]}'
                )
                return item["id"]

    def _is_track_in_playlist(self, tracks, track_name, artist):
        for track in tracks:
            if track_name.upper() in track["name"].upper(
            ):  #and artist in track["artists"]:
                return True
        return False


def _parse_tracks_from_file(file_handler):
    content = file_handler.read().splitlines()
    parsed_tracks = []
    for item in content:
        track = {}
        split = item.split("-")
        track["artists"] = split[0].strip()
        track["album"] = split[1].strip()
        track["name"] = split[2].strip()
        parsed_tracks.append(track)
    return parsed_tracks


def find_duplicates(args):
    spotify = SpotifyManager()
    duplicates = spotify.find_duplicates_in_playlists(args.playlist_a,
                                                      args.playlist_b)
    print('*' * 60)
    pprint(duplicates)
    print('*' * 60)


def add_tracks_to_playlist(args):
    tracks = _parse_tracks_from_file(args.file)
    print(len(tracks))
    spotify = SpotifyManager()
    spotify.add_tracks_to_playlist(tracks, args.playlist_name)


def merge_playlists():
    spotify = SpotifyManager()
    main = spotify.get_playlist_tracks("main")
    print(f"main: {len(main)}")
    names = [x["name"] for x in main]
    print("len main names: ", len(names))

    seen = set()
    uniq = []
    for x in main:
        if x["name"] not in seen:
            uniq.append(x["name"])
            seen.add(x["name"])
        else:
            print("*" * 120)
            print(x["name"])
    print(seen)
    print(len(seen))
    print(len(uniq))


# all_track_ids = [i["id"] for i in temp]
# main_id = spotify.get_playlist_id_by_name("main")
# spotify._spotify.user_playlist_add_tracks(USER_NAME, main_id,
#                                           all_track_ids)

#spotify._spotify.get_playlist_id_by_name("main")


def main():
    # args = parse_args()
    # print(args)
    # args.func(args)
    merge_playlists()


def parse_args():
    parser = argparse.ArgumentParser(description='Various spotify operations')
    subparsers = parser.add_subparsers(help="Different actions")

    duplicate_parser = subparsers.add_parser(
        "duplicates", help="Find duplicates in two playlists")
    duplicate_parser.add_argument('playlist_a', help='First playlist name')
    duplicate_parser.add_argument('playlist_b', help='Second playlist name')
    duplicate_parser.set_defaults(func=find_duplicates)

    add_list_parser = subparsers.add_parser(
        "add_from_file",
        help="Parse a file which contains tracks and add them to a playlist")
    add_list_parser.add_argument(
        "file",
        type=argparse.FileType('r'),
        help="Path to json file containing list of tracks")
    add_list_parser.add_argument(
        "--playlist-name",
        default="Amir",
        help="Name of the playlist to add tracks (default: 'Amir')")
    add_list_parser.set_defaults(func=add_tracks_to_playlist)

    parser.add_argument("--dry-run",
                        action="store_true",
                        default=False,
                        help="Just print actions")
    return parser.parse_args()


if __name__ == "__main__":
    main()
