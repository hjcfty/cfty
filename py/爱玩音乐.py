import re
import sys
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote
from pyquery import PyQuery as pq
from requests import Session, adapters
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.22a5.com"
        self.session = Session()
        adapter = adapters.HTTPAdapter(max_retries=Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]), pool_connections=20, pool_maxsize=50)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"}
        self.session.headers.update(self.headers)

    def getName(self): return "爱玩音乐"
    def isVideoFormat(self, url): return bool(re.search(r'\.(m3u8|mp4|mp3|m4a|flv)(\?|$)', url or "", re.I))
    def manualVideoCheck(self): return False
    def destroy(self): self.session.close()

    def homeContent(self, filter):
        classes = [{"type_name": n, "type_id": i} for n, i in [("电台","/radiolist/index.html"), ("歌单","/playtype/index.html"), ("专辑","/albumlist/index.html"), ("歌手","/singerlist/index/index/index/index.html"), ("高清MV","/mvlist/oumei.html"), ("新歌榜","/list/new.html"), ("TOP榜单","/list/top.html")]]
        filters = {p: d for p in [c["type_id"] for c in classes if "singer" not in c["type_id"]] if (d := self._fetch_filters(p))}
        
        if "/radiolist/index.html" not in filters:
            filters["/radiolist/index.html"] = [{"key": "id", "name": "分类", "value": [{"n": n, "v": v} for n,v in zip(["最新","最热","有声小说","相声","音乐","情感","国漫","影视","脱口秀","历史","儿童","教育","八卦","推理","头条"], ["index","hot","novel","xiangyi","music","emotion","game","yingshi","talkshow","history","children","education","gossip","tuili","headline"])]}]

        filters["/singerlist/index/index/index/index.html"] = [
            {"key": "area", "name": "地区", "value": [{"n": n, "v": v} for n,v in [("全部","index"),("华语","huayu"),("欧美","oumei"),("韩国","hanguo"),("日本","ribrn")]]},
            {"key": "sex", "name": "性别", "value": [{"n": n, "v": v} for n,v in [("全部","index"),("男","male"),("女","girl"),("组合","band")]]},
            {"key": "genre", "name": "流派", "value": [{"n": n, "v": v} for n,v in [("全部","index"),("流行","liuxing"),("电子","dianzi"),("摇滚","yaogun"),("嘻哈","xiha"),("R&B","rb"),("民谣","minyao"),("爵士","jueshi"),("古典","gudian")]]},
            {"key": "char", "name": "字母", "value": [{"n": "全部", "v": "index"}] + [{"n": chr(i), "v": chr(i).lower()} for i in range(65, 91)]}
        ]
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self): return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        url = tid
        if "/singerlist/" in tid:
            p = tid.split('/')
            if len(p) >= 6:
                url = "/".join(p[:2] + [extend.get(k, p[i]) for i, k in enumerate(["area", "sex", "genre"], 2)] + [f"{extend.get('char', 'index')}.html"])
        elif "id" in extend and extend["id"] not in ["index", "top"]:
            url = tid.replace("index.html", f"{extend['id']}.html").replace("top.html", f"{extend['id']}.html")
            if url == tid: url = f"{tid.rsplit('/', 1)[0]}/{extend['id']}.html"

        if pg > 1:
            sep = "/" if any(x in url for x in ["/singerlist/", "/radiolist/", "/mvlist/", "/playtype/", "/list/"]) else "_"
            url = re.sub(r'(_\d+|/\d+)?\.html$', f'{sep}{pg}.html', url)
        
        doc = self.getpq(url)
        return {"list": self._parse_list(doc(".play_list li, .video_list li, .pic_list li, .singer_list li, .ali li, .layui-row li, .base_l li"), tid), "page": pg, "pagecount": 9999, "limit": 90, "total": 999999}

    def searchContent(self, key, quick, pg="1"):
        return {"list": self._parse_list(self.getpq(f"/so/{quote(key)}/{pg}.html")(".base_l li, .play_list li"), "search"), "page": int(pg)}

    def detailContent(self, ids):
        url = self._abs(ids[0])
        doc = self.getpq(url)
        vod = {"vod_id": url, "vod_name": self._clean(doc("h1").text() or doc("title").text()), "vod_pic": self._abs(doc(".djpg img, .pic img, .djpic img").attr("src")), "vod_play_from": "爱玩音乐", "vod_content": ""}

        if any(x in url for x in ["/playlist/", "/album/", "/list/", "/singer/", "/special/", "/radio/", "/radiolist/"]):
            eps = self._get_eps(doc)
            page_urls = {self._abs(a.attr("href")) for a in doc(".page a, .dede_pages a, .pagelist a").items() if a.attr("href") and "javascript" not in a.attr("href")} - {url}
            if page_urls:
                with ThreadPoolExecutor(max_workers=5) as ex:
                    for r in as_completed([ex.submit(lambda u: self._get_eps(self.getpq(u)), u) for u in sorted(page_urls, key=lambda x: int(re.search(r'[_\/](\d+)\.html', x).group(1)) if re.search(r'[_\/](\d+)\.html', x) else 0)]):
                        eps.extend(r.result() or [])
            if eps:
                vod.update({"vod_play_from": "播放列表", "vod_play_url": "#".join(eps)})
                return {"list": [vod]}

        play_list = []
        if mid := re.search(r'/(song|mp3|radio|radiolist|radioplay)/([^/]+)\.html', url):
            lrc_url = f"{self.host}/plug/down.php?ac=music&lk=lrc&id={mid.group(2)}"
            play_list = [f"播放${self.e64('0@@@@' + url + '|||' + lrc_url)}"]
        
        elif vid := re.search(r'/(video|mp4)/([^/]+)\.html', url):
            with ThreadPoolExecutor(max_workers=3) as ex:
                fs = {ex.submit(self._api, "/plug/down.php", {"ac": "vplay", "id": vid.group(2), "q": q}): n for n, q in [("蓝光", 1080), ("超清", 720), ("高清", 480)]}
                play_list = [f"{fs[f]}${self.e64('0@@@@'+u)}" for f in as_completed(fs) if (u := f.result())]
            play_list.sort(key=lambda x: {"蓝":0, "超":1, "高":2}.get(x[0], 3))

        vod["vod_play_url"] = "#".join(play_list) if play_list else f"解析失败${self.e64('1@@@@'+url)}"
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = self.d64(id).split("@@@@")[-1]
        url, subt = raw.split("|||") if "|||" in raw else (raw, "")
        url = url.replace(r"\/", "/")

        if ".html" in url and not self.isVideoFormat(url):
            if mid := re.search(r'/(song|mp3|radio|radiolist|radioplay)/([^/]+)\.html', url):
                if r_url := self._api("/js/play.php", method="POST", data={"id": mid.group(2), "type": "music"}, headers={"Referer": url.replace("http://","https://"), "X-Requested-With": "XMLHttpRequest"}):
                    url = r_url if ".php" not in r_url else url
            elif vid := re.search(r'/(video|mp4)/([^/]+)\.html', url):
                with ThreadPoolExecutor(max_workers=3) as ex:
                    for f in as_completed([ex.submit(self._api, "/plug/down.php", {"ac": "vplay", "id": vid.group(2), "q": q}) for q in [1080, 720, 480]]):
                        if v_url := f.result():
                            url = v_url; break
        
        result = {"parse": 0, "url": url, "header": {"User-Agent": self.headers["User-Agent"]}}
        if "22a5.com" in url: result["header"]["Referer"] = self.host + "/"
        
        if subt:
            # 【关键】这里将 type 标记为 ssa，并加上 .ass 后缀，让 localProxy 进行转换
            proxy_lrc = f"{self.getProxyUrl()}&url={quote(subt)}&type=ssa&.ass"
            result["subs"] = [{
                "url": proxy_lrc,
                "name": "歌词",
                # 【关键】MIME类型改为 SSA
                "format": "text/x-ssa", 
                "selected": True
            }]
            
        return result

    def localProxy(self, param):
        url = unquote(param.get("url", ""))
        type_ = param.get("type")
        
        if type_ == "img":
            return [200, "image/jpeg", self.session.get(url, headers={"Referer": self.host + "/"}, timeout=5).content, {}]
        
        # 【关键】LRC 转 SSA 逻辑
        elif type_ == "ssa" or type_ == "lrc":
            try:
                r = self.session.get(url, headers={"Referer": self.host + "/"}, timeout=5)
                lrc_content = r.text
                
                # 执行转换
                ssa_content = self._lrc_to_ssa(lrc_content)
                
                # 返回 text/x-ssa 类型
                return [200, "text/x-ssa", ssa_content, {}]
            except:
                return [404, "text/plain", "Error", {}]
                
        return None

    def _lrc_to_ssa(self, lrc_text):
        # SSA 头文件，模仿饭太硬的样式
        ssa_header = """[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KTV,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = []
        # 解析 LRC: [mm:ss.xx]歌词
        regex = re.compile(r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)')
        
        time_text_list = []
        for line in lrc_text.splitlines():
            match = regex.search(line)
            if match:
                m, s, ms, text = match.groups()
                ms = ms if ms else "00"
                # 毫秒统一处理
                if len(ms) == 2: ms = int(ms) * 10
                elif len(ms) == 3: ms = int(ms)
                
                total_seconds = int(m) * 60 + int(s) + ms / 1000.0
                text = text.strip()
                if text: # 忽略空行
                    time_text_list.append((total_seconds, text))

        ssa_events = ""
        for i in range(len(time_text_list)):
            start_sec, text = time_text_list[i]
            # 计算结束时间：下一句开始时间，或者是当前句开始+5秒
            if i < len(time_text_list) - 1:
                end_sec = time_text_list[i+1][0]
                # 如果下一句间隔太远（超过10秒），截断
                if end_sec - start_sec > 10:
                    end_sec = start_sec + 5
            else:
                end_sec = start_sec + 5
            
            start_fmt = self._sec_to_ssa_time(start_sec)
            end_fmt = self._sec_to_ssa_time(end_sec)
            
            ssa_events += f"Dialogue: 0,{start_fmt},{end_fmt},KTV,,0,0,0,,{text}\n"

        return ssa_header + ssa_events

    def _sec_to_ssa_time(self, seconds):
        # SSA时间格式: h:mm:ss.cc (百分之一秒)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _parse_list(self, items, tid=""):
        res = []
        for li in items.items():
            a = li("a").eq(0)
            if not (href := a.attr("href")) or href == "/" or any(x in href for x in ["/user/", "/login/", "javascript"]): continue
            if not (name := self._clean(li(".name").text() or a.attr("title") or a.text())): continue
            pic = self._abs((li("img").attr("src") or "").replace('120', '500'))
            res.append({"vod_id": self._abs(href), "vod_name": name, "vod_pic": f"{self.getProxyUrl()}&url={pic}&type=img" if pic else "", "style": {"type": "oval" if "/singer/" in href else ("list" if any(x in tid for x in ["/list/", "/playtype/", "/albumlist/"]) else "rect"), "ratio": 1 if "/singer/" in href else 1.33}})
        return res

    def _get_eps(self, doc):
        eps = []
        for li in doc(".play_list li, .song_list li, .music_list li").items():
            if not (a := li("a").eq(0)).attr("href") or not re.search(r'/(song|mp3|radio|radiolist|radioplay)/', a.attr("href")): continue
            full_url = self._abs(a.attr("href"))
            
            lrc_part = ""
            mid = re.search(r'/(song|mp3|radio|radiolist|radioplay)/([^/]+)\.html', full_url)
            if mid:
                lrc_url = f"{self.host}/plug/down.php?ac=music&lk=lrc&id={mid.group(2)}"
                lrc_part = f"|||{lrc_url}"
            
            eps.append(f"{self._clean(a.text() or li('.name').text())}${self.e64('0@@@@' + full_url + lrc_part)}")
        return eps

    def _clean(self, text): return re.sub(r'(爱玩音乐网|视频下载说明|视频下载地址|www\.2t58\.com|MP3免费下载|LRC歌词下载|全部歌曲|\[第\d+页\]|刷新|每日推荐|最新|热门|推荐|MV|高清|无损)', '', text or "", flags=re.I).strip()

    def _fetch_filters(self, url):
        doc, filters = self.getpq(url), []
        for i, group in enumerate([doc(s) for s in [".ilingku_fl", ".class_list", ".screen_list", ".box_list", ".nav_list"] if doc(s)]):
            opts, seen = [{"n": "全部", "v": "top" if "top" in url else "index"}], set()
            for a in group("a").items():
                if (v := (a.attr("href") or "").split("?")[0].rstrip('/').split('/')[-1].replace('.html','')) and v not in seen:
                    opts.append({"n": a.text().strip(), "v": v}); seen.add(v)
            if len(opts) > 1: filters.append({"key": f"id{i}" if i else "id", "name": "分类", "value": opts})
        return filters

    def _api(self, path, params=None, method="GET", headers=None, data=None):
        try:
            h = self.headers.copy()
            if headers: h.update(headers)
            r = (self.session.post if method == "POST" else self.session.get)(f"{self.host}{path}", params=params, data=data, headers=h, timeout=10, allow_redirects=False)
            if loc := r.headers.get("Location"): return self._abs(loc.strip())
            return self._abs(r.json().get("url", "").replace(r"\/", "/")) or (r.text.strip() if r.text.strip().startswith("http") else "")
        except: return ""

    def getpq(self, url):
        import time
        for _ in range(2): 
            try: return pq(self.session.get(self._abs(url), timeout=5).text)
            except: time.sleep(0.1)
        return pq("<html></html>")

    def _abs(self, url): return url if url.startswith("http") else (f"{self.host}{'/' if not url.startswith('/') else ''}{url}" if url else "")
    def e64(self, text): return b64encode(text.encode("utf-8")).decode("utf-8")
    def d64(self, text): return b64decode(text.encode("utf-8")).decode("utf-8")
