import base64
import html
import json
import os
import urllib.request
from unidecode import unidecode
from mutagen.mp4 import MP4, MP4Cover
from pySmartDL import SmartDL
import unicodedata
import re
from .helper import argManager
from .pyDes import *


class Manager:
    def __init__(self):
        self.unicode = str
        self.args = argManager()
        self.des_cipher = self.setDecipher()

    def setDecipher(self):
        return des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)

    def get_dec_url(self, enc_url):
        enc_url = base64.b64decode(enc_url.strip())
        dec_url = self.des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode("utf-8")
        dec_url = dec_url.replace("_96.mp4", "_320.mp4")
        return dec_url

    def format_filename(self, filename) -> str:
        filename = html.unescape(filename)
        filename = filename.replace('"', "'")
        for c in "&#:/<>?*|":
            filename.replace(c, "-")
        filename = filename.replace(", ", "_")
        filename = re.sub(r"[^\w\s]-", "", filename.lower())
        filename = re.sub(r"[-\s]+", "-", filename).strip("-_").strip(".")
        filename = unidecode(filename)
        filename = (
            unicodedata.normalize("NFKD", filename)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return filename

    def get_download_location(self, *args):
        if self.args.outFolder is None:
            location = os.getcwd()
        else:
            location = self.args.outFolder
        for folder in args:
            folder = self.format_filename(folder)
            location = os.path.join(location, folder)
        return location[:250] + ".m4a"

    def start_download(self, filename, location, dec_url):
        if len(filename) < 1 or filename == "":
            print(f"Error Downloding {location}")
        if os.path.isfile(location):
            print("Downloaded {0}".format(filename))
            return False
        else:
            print("Downloading {0}".format(filename))
            print(location)
            obj = SmartDL(dec_url, location)
            obj.start()
            return True

    def downloadSongs(
        self,
        songs_json,
        album_name="songs",
        artist_name="Non-Artist",
        is_playlist=False,
    ):

        filename = None
        playlist_name = None
        dec_url = None
        if is_playlist:
            playlist_name = songs_json.get("title")
            songslist = songs_json.get("list")
            print(f"[*] Downloading Playlist {playlist_name}")
            pass
        else:
            album_name = unidecode(songs_json.get("name"))
            artist_name = unidecode(songs_json.get("primary_artists"))
            songslist = songs_json.get("songs")
            print(f"[*] Downloading album {album_name}")
            pass

        for song in songslist:

            if song["id"] == "":
                continue

            if is_playlist:
                artist_name = ", ".join(
                    [
                        unidecode(artist["name"])
                        for artist in song["more_info"]["artistMap"]["primary_artists"]
                    ]
                )

                album_name = (
                    unidecode(song.get("more_info").get("album"))
                    if song.get("more_info").get("album")
                    else ""
                )

            try:
                if is_playlist:
                    dec_url = self.get_dec_url(song["more_info"]["encrypted_media_url"])
                    filename = self.format_filename(
                        song.get("title") + "_" + song.get("id")
                    )
                else:
                    dec_url = self.get_dec_url(song.get("encrypted_media_url"))
                    filename = self.format_filename(
                        song.get("song") + "_" + song.get("id")
                    )
                song["dec_url"] = dec_url
            except Exception as e:
                print("Download Error: {0}".format(e))

            assert filename != ""

            try:
                location = (
                    self.get_download_location(
                        playlist_name, artist_name, album_name, filename
                    )
                    if is_playlist
                    else self.get_download_location(artist_name, album_name, filename)
                )
                song["location"] = location
                has_downloaded = self.start_download(filename, location, dec_url)
                assert os.access(os.path.dirname(location), os.W_OK) == True
                if has_downloaded:
                    name = songs_json.get("title")
                    try:
                        self.addtags(location, song, name, artist_name, is_playlist)
                    except Exception as e:
                        print("============== Error Adding Meta Data ==============")
                        print("Error : {0}".format(e))
                    print("\n")
            except Exception as e:
                print("Download Error : {0}".format(e))

        if is_playlist:
            with open(playlist_name + ".json", "w") as jsonfile:
                json.dump(songs_json, jsonfile, indent=4, sort_keys=True)

    def addtags(
        self, filename, json_data, playlist_name, artist_name, is_playlist=False
    ):
        audio = MP4(filename)
        audio["\xa9ART"] = html.unescape(self.unicode(artist_name))
        audio["aART"] = html.unescape(self.unicode(artist_name))
        audio["\xa9gen"] = html.unescape(self.unicode(playlist_name))
        audio["\xa9day"] = html.unescape(self.unicode(json_data["year"]))
        audio["disk"] = [(1, 1)]

        if is_playlist:
            audio["\xa9alb"] = html.unescape(
                self.unicode(json_data["more_info"]["album"])
            )
            audio["\xa9wrt"] = html.unescape(
                self.unicode(json_data["more_info"]["music"])
            )
            audio["cprt"] = html.unescape(self.unicode(json_data["more_info"]["label"]))
            audio["\xa9nam"] = html.unescape(self.unicode(json_data["title"]))
        else:
            audio["\xa9alb"] = html.unescape(self.unicode(json_data["album"]))
            audio["\xa9wrt"] = html.unescape(self.unicode(json_data["music"]))
            audio["cprt"] = html.unescape(self.unicode(json_data["label"]))
            audio["\xa9nam"] = html.unescape(self.unicode(json_data["song"]))

        audio["desc"] = (
            html.unescape(self.unicode(json_data["header_desc"]))
            if "header_desc" in json_data
            else ""
        )
        cover_url = json_data["image"][:-11] + "500x500.jpg"
        fd = urllib.request.urlopen(cover_url)
        cover = MP4Cover(
            fd.read(),
            getattr(
                MP4Cover, "FORMAT_PNG" if cover_url.endswith("png") else "FORMAT_JPEG"
            ),
        )
        fd.close()
        audio["covr"] = [cover]
        audio.save()
