'''
Function:
    Implementation of SoundCloudMusicClient Utils
Author:
    Zhenchao Jin
WeChat Official Account (微信公众号):
    Charles的皮卡丘
'''
import re
import requests
from pathlib import Path
from pywidevine.cdm import Cdm
from urllib.parse import urljoin
from pywidevine.pssh import PSSH
from pywidevine.device import Device


'''SoundCloudMusicClientUtils'''
class SoundCloudMusicClientUtils():
    DEVICE_WVD_PATH = Path(__file__).resolve().parents[2] / "modules" / "wvds" / "musicdl_charlespikachu_device_v1.wvd"
    '''getwidevinekeys'''
    @staticmethod
    def getwidevinekeys(pssh_b64: str, license_token: str, headers: dict = None, cookies: dict = None, request_overrides: dict = None):
        session_id = (cdm := Cdm.from_device(Device.load(SoundCloudMusicClientUtils.DEVICE_WVD_PATH))).open()
        challenge, license_url = cdm.get_license_challenge(session_id, PSSH(pssh_b64)), f"https://license.media-streaming.soundcloud.cloud/playback/widevine?license_token={license_token}"
        (default_headers := {"Content-Type": "application/octet-stream"}).update((headers := headers or {}))
        (resp := requests.post(license_url, headers=default_headers, data=challenge, cookies=(cookies := cookies or {}), **(request_overrides := request_overrides or {}))).raise_for_status()
        cdm.parse_license(session_id, resp.content)
        keys = [f"{(key.kid.hex() if isinstance(key.kid, bytes) else key.kid.hex)}:{(key.key.hex() if isinstance(key.key, bytes) else key.key.hex)}" for key in cdm.get_keys(session_id) if key.type == "CONTENT"]
        cdm.close(session_id)
        return keys
    '''extractpssh'''
    @staticmethod
    def extractpssh(m3u8_url: str, headers: dict = None, cookies: dict = None, request_overrides: dict = None):
        (resp := requests.get(m3u8_url, headers=(headers := headers or {}), cookies=(cookies := cookies or {}), **(request_overrides := request_overrides or {}))).raise_for_status()
        if "#EXT-X-STREAM-INF" in (m3u8_text := resp.text): m3u8_text = (lambda lines: next((requests.get(urljoin(m3u8_url, lines[i + 1].strip()), headers=headers, cookies=cookies, **request_overrides).text for i, line in enumerate(lines) if line.startswith("#EXT-X-STREAM-INF") and i + 1 < len(lines)), m3u8_text))(m3u8_text.splitlines())
        return re.search(r'URI="data:text/plain;base64,([^"]+)"', m3u8_text).group(1)