#小心儿悠悠
from urllib.parse import quote
from base.spider import Spider
import requests

class Spider(Spider):
    def getName(self):
        return "酷音乐"

    def init(self, extend):
        self.official_api = "https://www.kuwo.cn/api/www"
        self.search_api = "https://kuwo.cn/search/searchMusicBykeyWord"
        self.parse_api = "https://api.cenguigui.cn/api/kuwo/"
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.kuwo.cn/',
            'Cookie': 'Hm_lvt_cdb524f42f0ce19b169a8071123a4797=1749005756; HMACCOUNT=7400D86664661689; _ga=GA1.2.834396397.1749005756; _gid=GA1.2.607093385.1749005756; Hm_lpvt_cdb524f42f0ce19b169a8071123a4797=1749045577; _ga_ETPBRPM9ML=GS2.2.s1749045564$o3$g1$t1749045595$j29$l0$h0; Hm_Iuvt_cdb524f42f23cer9b268564v7y735ewrq2324=2XyC6cxC5wTf2jcP3W5nECECcjdrDFfN',
            'Host': 'kuwo.cn',
            'Secret': '1108f2e127441068eb52f4f779d0d27d3b98c4b972b9d9446aea1febc2c003c201473e73'
        }

    def homeContent(self, filter):
        categories = [
            {"type_id": "93", "type_name": "酷我飙升榜"},
            {"type_id": "17", "type_name": "酷我新歌榜"},
            {"type_id": "16", "type_name": "酷我热歌榜"},
            {"type_id": "158", "type_name": "抖音热歌排行榜"},
            {"type_id": "176", "type_name": "万物DJ榜"},
            {"type_id": "336", "type_name": "会员飙升榜"},
            {"type_id": "331", "type_name": "会员爱听排行榜"},
            {"type_id": "330", "type_name": "会员新歌榜"},
            {"type_id": "26", "type_name": "经典怀旧榜"},
            {"type_id": "153", "type_name": "网红新歌榜"},
            {"type_id": "278", "type_name": "古风音乐榜"},
            {"type_id": "284", "type_name": "酷我热评榜"},
            {"type_id": "64", "type_name": "影视金曲榜"},
            {"type_id": "242", "type_name": "极品电音榜"},
            {"type_id": "184", "type_name": "流行趋势榜"},
            {"type_id": "154", "type_name": "酷我综艺榜"},
            {"type_id": "329", "type_name": "酷我说唱榜"},
            {"type_id": "291", "type_name": "爆笑相声榜"},
            {"type_id": "69", "type_name": "儿童歌曲榜"},
            {"type_id": "344", "type_name": "儿童故事榜"},
            {"type_id": "328", "type_name": "车载歌曲榜"},
            {"type_id": "297", "type_name": "跑步健身榜"},
            {"type_id": "255", "type_name": "KTV点唱榜"}
        ]
        
        return {"class": categories}

    def categoryContent(self, cid, pg, filter, ext):
        try:
            url = f"{self.official_api}/bang/bang/musicList?bangId={cid}&pn={pg}&rn=20&httpsStatus=1"
            
            headers = self.headers.copy()
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('code') == 200:
                videos = []
                songs = data.get('data', {}).get('musicList', [])
                
                for song in songs:
                    rid = song.get('rid', '')
                    videos.append({
                        "vod_id": str(rid),
                        "vod_name": song.get('name', ''),
                        "vod_pic": song.get('pic', ''),
                        "vod_remarks": song.get('artist', '')
                    })
                
                return {
                    'list': videos,
                    'page': pg,
                    'pagecount': 999,
                    'limit': 20,
                    'total': len(songs)
                }
                
        except Exception:
            pass
            
        return {'list': []}

    def detailContent(self, ids):
        try:
            url = f"https://kuwo.cn/api/www/music/musicInfo?mid={ids[0]}&httpsStatus=1"
            
            headers = self.headers.copy()
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('code') == 200:
                info = data.get('data', {})
                rid = info.get('rid', ids[0])
                song_name = info.get('name', '未知歌曲')
                
                play_urls = []
                qualities = ['HiRes音质', '无损音质', '高音质', '标准音质']
                for quality in qualities:
                    play_urls.append(f"{song_name}${rid}")
                
                return {'list': [{
                    "vod_id": rid,
                    "vod_name": song_name,
                    "vod_actor": info.get('artist', '未知歌手'),
                    "vod_year": info.get('releaseDate', '').split('-')[0] if info.get('releaseDate') else '',
                    "vod_content": info.get('albuminfo', ''),
                    "vod_remarks": info.get('album', ''),
                    "vod_play_from": '$$$'.join(qualities),
                    "vod_play_url": '$$$'.join(play_urls)
                }]}
                
        except Exception:
            pass
            
        return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            quality_map = {
                'HiRes音质': 'master',
                '无损音质': 'lossless',
                '高音质': 'high',
                '标准音质': 'standard'
            }
            
            level = quality_map.get(flag, 'high')
            parse_url = f"{self.parse_api}?rid={id}&level={level}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.kuwo.cn/'
            }
            
            response = requests.get(parse_url, headers=headers, timeout=10)
            data = response.json()
            
            url = ""
            if data.get('code') == 200:
                url = data.get('data', {}).get('url', '') or data.get('url', '') or data.get('data', '')
            
            return {
                "parse": 0,
                "playUrl": '',
                "url": url,
                "header": headers
            }
            
        except Exception:
            return {
                "parse": 0, 
                "playUrl": '', 
                "url": '', 
                "header": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.kuwo.cn/'
                }
            }

    def searchContent(self, key, quick, pg="1"):
        try:
            encoded_key = quote(key)
            page_num = int(pg) - 1
            
            url = f"{self.search_api}?vipver=1&client=kt&ft=music&cluster=0&strategy=2012&encoding=utf8&rformat=json&mobi=1&issubtitle=1&show_copyright_off=1&pn={page_num}&rn=20&all={encoded_key}"
            
            headers = self.headers.copy()
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('abslist'):
                videos = []
                songs = data.get('abslist', [])
                
                for song in songs:
                    rid = song.get('MUSICRID', '').replace('MUSIC_', '') if song.get('MUSICRID') else ''
                    imagePath = song.get('web_albumpic_short', '')
                    imageSrc = f"https://img2.kuwo.cn/star/albumcover/{imagePath}" if imagePath else ""
                    
                    videos.append({
                        "vod_id": rid,
                        "vod_name": song.get('SONGNAME', ''),
                        "vod_pic": imageSrc,
                        "vod_remarks": song.get('ARTIST', '')
                    })
                
                return {
                    'list': videos,
                    'page': pg,
                    'pagecount': 1,
                    'limit': 20,
                    'total': len(songs)
                }
                
        except Exception:
            pass
            
        return {'list': []}
