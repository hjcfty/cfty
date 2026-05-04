# -*- coding: utf-8 -*-
# by @天涯
import json
import re
import sys
import time
from base64 import b64decode, b64encode
import requests
from urllib.parse import quote
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host = "https://ww66.taiee.lol"
        
        # ============ 解析器配置 ============
        # 所有解析器都在这个列表里，包括直接嗅探的解析器
        self.parsers = [           
            "http://nm.4688888.xyz/jiexi.php?data=093207528aec95afa4616e7afb8e2649&url=",  # 牛马解析
            "http://120.46.190.255//jiexi.php?data=f603bb5f52a0cc1db4064599c3cc9abf&url=",  # 小白解析
            "http://8.155.50.80/xiayexk.php?url=",  # 夏夜解析
            "https://qsy.wya6.cn/parse.php?url=",  # 无意云解析
            "http://zhuimi.摸鱼儿.com/moyu/zhuimi?token=uZBC6q6w&url=",  # 摸鱼解析
            "http://yoyo168.zabc.net/getjx.php?host=http://154.222.26.58:7788&key=guodan2004031600&api=6d735c167eeda72b836cf382e4863f3f&v="  # 呦呦解析
            "https://pp1301239612013983305599.tai2tai.sbs/?url=",  # 太乙嗅探
            "https://jx.xmflv.com/?url=",  #虾米嗅探
        ]
        
        # 直接嗅探的解析器特征（部分匹配即可）
        self.direct_sniff_keys = [
            "tai2tai.sbs",
            "jx.xmflv.com",
            # 可以添加其他直接嗅探解析器的特征
        ]

    def getName(self):
        return "太乙电影（完整修复版）"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Referer': f'https://ww66.taiee.lol'
    }

    config = {
        "20": [{"key": "by", "name": "排序", "value": [
            {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}
        ]}],
        "21": [{"key": "by", "name": "排序", "value": [
            {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}
        ]}],
        "22": [{"key": "by", "name": "排序", "value": [
            {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}
        ]}],
        "23": [{"key": "by", "name": "排序", "value": [
            {"n": "按最新", "v": "time"}, {"n": "按最热", "v": "hits"}, {"n": "按评分", "v": "score"}
        ]}]
    }

    def homeContent(self, filter):
        classes = [
            {'type_name': '电影', 'type_id': '20'},
            {'type_name': '剧集', 'type_id': '21'},
            {'type_name': '综艺', 'type_id': '22'},
            {'type_name': '动漫', 'type_id': '23'}
        ]
        
        videos = []
        try:
            api_data = self._get_api_data('20', 1, {'by': 'time'})
            if api_data and 'list' in api_data:
                videos = api_data['list'][:15]
        except Exception as e:
            print(f"首页数据获取失败: {str(e)}")
            videos = []
        
        return {'class': classes, 'filters': self.config, 'list': videos}

    def homeVideoContent(self):
        pass

    def _get_api_data(self, tid, pg, extend=None):
        if extend is None:
            extend = {}
            
        api_url = f"{self.host}/index.php/ds_api/vod"
        params = {'type': str(tid), 'page': str(pg), 'by': extend.get('by', 'time')}
        
        try:
            response = requests.post(api_url, data=params, headers=self.headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 1:
                    videos = []
                    for item in data.get('list', []):
                        vod_id = item.get('vod_id', '')
                        if vod_id:
                            videos.append({
                                'vod_id': f"/index.php/vod/detail/id/{vod_id}.html",
                                'vod_name': item.get('vod_name', ''),
                                'vod_pic': item.get('vod_pic', ''),
                                'vod_remarks': item.get('vod_remarks', ''),
                                'vod_year': ''
                            })
                    
                    return {
                        'list': videos,
                        'page': data.get('page', 1),
                        'pagecount': data.get('pagecount', 9999),
                        'limit': data.get('limit', 40),
                        'total': data.get('total', 999999)
                    }
        except Exception as e:
            print(f"API请求失败: {str(e)}")
        
        return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 40, 'total': 0}

    def categoryContent(self, tid, pg, filter, extend):
        if not extend:
            extend = {}
        if 'by' not in extend:
            extend['by'] = 'time'
        
        data = self._get_api_data(tid, pg, extend)
        
        return {
            'list': data.get('list', []),
            'page': int(pg),
            'pagecount': data.get('pagecount', 9999),
            'limit': data.get('limit', 40),
            'total': data.get('total', 999999)
        }

    def detailContent(self, ids):
        try:
            detail_url = ids[0]
            print(f"详情页URL: {detail_url}")
            
            if detail_url.startswith('/'):
                detail_url = f"{self.host}{detail_url}"
            
            response = requests.get(detail_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return {'list': []}
            
            html = response.text
            
            # 提取影片名称
            vod_name = ''
            title_match = re.search(r'<title>([^<]+)</title>', html)
            if title_match:
                vod_name = title_match.group(1).split('_')[0].split('-')[0].strip()
            
            # 提取封面图片
            vod_pic = ''
            pic_match = re.search(r'<img[^>]*class="lazy lazy1"[^>]*data-src="([^"]+)"', html)
            if pic_match:
                vod_pic = pic_match.group(1)
                if vod_pic and not vod_pic.startswith('http'):
                    vod_pic = f"https:{vod_pic}" if vod_pic.startswith('//') else vod_pic
            
            # 提取备注信息
            vod_remarks = ''
            remarks_match = re.search(r'<span class="public-list-prb[^"]*">([^<]+)</span>', html)
            if remarks_match:
                vod_remarks = remarks_match.group(1)
            
            # 提取简介
            vod_content = ''
            desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
            if desc_match:
                vod_content = desc_match.group(1).strip()
            
            play_from = []
            play_url = []
            
            print("开始提取线路和选集信息...")
            
            # 提取线路名称
            line_names = []
            lines_section = re.search(r'<div class="anthology-tab[^"]*">(.*?)</div>', html, re.DOTALL)
            if lines_section:
                lines_html = lines_section.group(1)
                line_matches = re.findall(r'>([A-Z]{2})<', lines_html)
                if not line_matches:
                    line_matches = re.findall(r'&nbsp;([A-Z]{2})', lines_html)
                if not line_matches:
                    line_matches = re.findall(r'([A-Z]{2})</a>', lines_html)
                
                if line_matches:
                    for line in line_matches:
                        if line not in line_names:
                            line_names.append(line)
                    print(f"从线路区域提取到线路: {line_names}")
            
            # 如果没找到，使用默认线路
            if not line_names:
                line_names = ["TX", "IQ", "YK", "MG"]
                print(f"使用默认线路: {line_names}")
            
            # 提取播放链接并按sid分组
            play_pattern = r'href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]+)</a>'
            all_play_links = re.findall(play_pattern, html)
            
            if all_play_links:
                print(f"找到 {len(all_play_links)} 个播放链接")
                
                # 按sid分组
                line_dict = {}
                for href, name in all_play_links:
                    sid_match = re.search(r'/sid/(\d+)/', href)
                    if sid_match:
                        sid = sid_match.group(1)
                        if sid not in line_dict:
                            line_dict[sid] = []
                        
                        full_url = f"{self.host}{href}"
                        line_dict[sid].append(f"{name}${full_url}")
                
                print(f"按sid分组结果: {sorted(line_dict.keys())}")
                
                # 将线路名称与sid关联
                sorted_sids = sorted(line_dict.keys(), key=int)
                
                # 确保有足够的线路名称
                while len(line_names) < len(sorted_sids):
                    line_names.append(f"备用{len(line_names)+1}")
                
                # 创建线路
                for i, sid in enumerate(sorted_sids):
                    if i < len(line_names):
                        line_name = line_names[i]
                    else:
                        line_name = f"线路{sid}"
                    
                    episodes = line_dict[sid]
                    if episodes:
                        play_from.append(line_name)
                        play_url.append('#'.join(episodes))
                        print(f"线路 {line_name} (sid={sid}): {len(episodes)}个选集")
            else:
                # 备用方法：查找其他格式的播放链接
                alt_pattern = r'href="(/vod/play/[^"]+)"[^>]*>([^<]+)</a>'
                alt_links = re.findall(alt_pattern, html)
                
                if alt_links:
                    # 使用第一个线路名称
                    line_name = line_names[0] if line_names else "播放"
                    play_from.append(line_name)
                    episodes = []
                    for href, name in alt_links[:1]:
                        full_url = f"{self.host}{href}"
                        episodes.append(f"{name}${full_url}")
                    play_url.append('#'.join(episodes))
            
            # 如果还是没有找到，使用默认线路
            if not play_from:
                print("未找到播放链接，使用默认线路")
                play_from.append(line_names[0] if line_names else "默认线路")
                play_url.append("暂无资源$#")
            
            print(f"最终线路名称: {play_from}")
            
            vod = {
                'vod_id': detail_url,
                'vod_name': vod_name if vod_name else '未知影片',
                'vod_pic': vod_pic if vod_pic else '',
                'vod_year': '',
                'vod_remarks': vod_remarks if vod_remarks else '',
                'vod_actor': '',
                'vod_director': '',
                'vod_content': vod_content if vod_content else '',
                'vod_play_from': '$$$'.join(play_from) if play_from else '',
                'vod_play_url': '$$$'.join(play_url) if play_url else ''
            }
            
            return {'list': [vod]}
                
        except Exception as e:
            print(f"详情页异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """完整修复的搜索功能"""
        print(f"搜索关键词: {key}, 页码: {pg}")
        
        try:
            # 构建搜索URL
            if int(pg) > 1:
                search_url = f"{self.host}/index.php/vod/search/page/{pg}/wd/{quote(key)}.html"
            else:
                search_url = f"{self.host}/index.php/vod/search.html"
                params = {'wd': key}
            
            print(f"搜索URL: {search_url}")
            
            headers = self.headers.copy()
            if int(pg) > 1:
                response = requests.get(search_url, headers=headers, timeout=10)
            else:
                response = requests.get(search_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                
                # 检查是否有搜索结果
                if "没有找到相关视频" in html or "search-list" not in html:
                    print("未找到相关视频")
                    return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 20, 'total': 0}
                
                videos = []
                
                # 使用正则提取搜索结果
                # 首先提取整个搜索结果区域
                search_pattern = r'<div class="vod-detail style-detail cor4 search-list">(.*?)</div>\s*</div>\s*</div>'
                search_match = re.search(search_pattern, html, re.DOTALL)
                
                if search_match:
                    content = search_match.group(1)
                    
                    # 提取详情页链接
                    detail_match = re.search(r'href="(/index\.php/vod/detail/id/\d+\.html)"', content)
                    if detail_match:
                        detail_url = detail_match.group(1)
                        
                        # 提取标题
                        title_match = re.search(r'<h3[^>]*class="slide-info-title hide"[^>]*>([^<]+)</h3>', content)
                        if not title_match:
                            title_match = re.search(r'<h3[^>]*>([^<]+)</h3>', content)
                        
                        title = title_match.group(1).strip() if title_match else key
                        
                        # 提取封面图片
                        pic_match = re.search(r'data-src="([^"]+)"', content)
                        pic = pic_match.group(1) if pic_match else ""
                        
                        # 提取备注
                        remarks_match = re.search(r'<span class="slide-info-remarks cor5">([^<]+)</span>', content)
                        remarks = remarks_match.group(1) if remarks_match else ""
                        
                        # 提取年份
                        year_match = re.search(r'/year/(\d{4})\.html', content)
                        year = year_match.group(1) if year_match else ""
                        
                        # 格式化URL
                        if detail_url.startswith('/'):
                            detail_url = f"{self.host}{detail_url}"
                        
                        if pic and not pic.startswith('http'):
                            pic = f"https:{pic}" if pic.startswith('//') else pic
                        
                        videos.append({
                            'vod_id': detail_url,
                            'vod_name': title,
                            'vod_pic': pic,
                            'vod_remarks': remarks,
                            'vod_year': year
                        })
                else:
                    # 备用提取方法
                    print("使用备用提取方法")
                    
                    # 提取所有可能的影片项
                    item_pattern = r'<div[^>]*class="detail-pic"[^>]*>.*?data-src="([^"]+)".*?<a[^>]*href="(/index\.php/vod/detail/id/\d+\.html)"[^>]*>.*?<h3[^>]*>([^<]+)</h3>'
                    matches = re.findall(item_pattern, html, re.DOTALL)
                    
                    for pic, href, title in matches:
                        # 提取备注信息
                        remarks = ""
                        # 在href附近查找备注
                        remarks_area = html[html.find(href):html.find(href)+500]
                        remarks_match = re.search(r'<span[^>]*class="[^"]*remarks[^"]*"[^>]*>([^<]+)</span>', remarks_area)
                        if remarks_match:
                            remarks = remarks_match.group(1)
                        
                        # 格式化URL
                        if href.startswith('/'):
                            href = f"{self.host}{href}"
                        
                        if pic and not pic.startswith('http'):
                            pic = f"https:{pic}" if pic.startswith('//') else pic
                        
                        videos.append({
                            'vod_id': href,
                            'vod_name': title.strip(),
                            'vod_pic': pic,
                            'vod_remarks': remarks,
                            'vod_year': ""
                        })
                
                # 提取总页数
                pagecount = 1
                # 查找分页信息
                page_pattern = r'<a[^>]*href=[^>]*/page/(\d+)/wd/[^>]*>'
                pages = re.findall(page_pattern, html)
                if pages:
                    try:
                        page_numbers = [int(p) for p in pages]
                        if page_numbers:
                            pagecount = max(page_numbers)
                    except:
                        pass
                
                # 如果没有找到分页，但当前页有结果，假设总页数为当前页或当前页+1
                if videos and pagecount == 1 and int(pg) == 1:
                    pagecount = 2  # 假设至少还有一页
                
                print(f"搜索到 {len(videos)} 个结果，总页数: {pagecount}")
                
                return {
                    'list': videos,
                    'page': int(pg),
                    'pagecount': pagecount,
                    'limit': 20,
                    'total': len(videos) * pagecount if pagecount > 1 else len(videos)
                }
            else:
                print(f"搜索请求失败，状态码: {response.status_code}")
                
        except Exception as e:
            print(f"搜索异常: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 20, 'total': 0}

    def playerContent(self, flag, id, vipFlags):
        print(f"=== playerContent 被调用 ===")
        print(f"线路标识: {flag}")
        print(f"原始播放地址: {id}")
        
        # 1. 提取真实的视频地址
        video_url = self.extract_video_url(id)
        print(f"提取到的视频地址: {video_url}")
        
        # 2. 检查是否已经是m3u8直链
        if video_url.endswith('.m3u8') or '.m3u8?' in video_url or '#EXTM3U' in video_url:
            print(f"已经是m3u8直链")
            return {
                'parse': 0,
                'url': video_url,
                'header': self.headers
            }
        
        # 3. 尝试所有解析器（按优先级）
        for i, parser in enumerate(self.parsers):
            try:
                # 检查是否是直接嗅探的解析器
                is_direct_sniff = any(key in parser for key in self.direct_sniff_keys)
                
                parsed_url = f"{parser}{quote(video_url)}"
                print(f"\n尝试解析器 {i+1}: {parser[:50]}...")
                
                if is_direct_sniff:
                    # ✅ 直接嗅探的解析器：直接返回给壳子
                    print(f"✓ 直接嗅探解析器，返回给壳子")
                    return {
                        'parse': 1,
                        'url': parsed_url,
                        'header': self.headers
                    }
                else:
                    # 普通解析器：先检查是否可用
                    response = requests.get(
                        parsed_url, 
                        headers=self.headers, 
                        timeout=5,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # 检查是否是测试视频
                        if self.is_test_video(content):
                            print(f"解析器返回测试视频，跳过")
                            continue
                        
                        # 检查是否返回了m3u8内容
                        if '#EXTM3U' in content:
                            print(f"✓ 解析器返回m3u8内容")
                            return {
                                'parse': 0,
                                'url': parsed_url,
                                'header': self.headers
                            }
                        
                        # 检查是否返回了JSON
                        if content.strip().startswith('{'):
                            try:
                                data = json.loads(content)
                                if 'url' in data and data['url'] and '.m3u8' in data['url']:
                                    print(f"✓ 解析器返回m3u8地址")
                                    return {
                                        'parse': 0,
                                        'url': data['url'],
                                        'header': self.headers
                                    }
                            except:
                                pass
                        
                        # 解析器工作正常但不是标准格式
                        print(f"✓ 解析器工作正常，返回给壳子")
                        return {
                            'parse': 1,
                            'url': parsed_url,
                            'header': self.headers
                        }
                    else:
                        print(f"解析器 {i+1} HTTP状态码: {response.status_code}")
                        
            except Exception as e:
                print(f"解析器 {i+1} 失败: {e}")
                continue
        
        # 4. ✅ 所有解析器都失败（包括直接嗅探的解析器）
        print(f"✗ 所有解析器都失败！调用壳子解析")
        
        # ✅ 按照您例子的格式返回，调用壳子解析
        return {
            'jx': 1,        # 按照例子格式
            'playUrl': '',  # 按照例子格式
            'parse': 1,     # 调用壳子解析
            'url': video_url,  # 原视频地址
            'header': self.headers
        }
    
    def extract_video_url(self, play_url):
        """
        从播放页提取真实的视频地址
        """
        print(f"尝试提取视频地址: {play_url}")
        
        try:
            response = requests.get(play_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return play_url
            
            html = response.text
            
            # 查找player_aaaa变量
            player_match = re.search(r'var player_aaaa\s*=\s*({.*?});', html, re.DOTALL)
            if player_match:
                player_data = player_match.group(1)
                print(f"找到player_aaaa数据")
                
                # 直接提取url字段
                url_match = re.search(r'"url"\s*:\s*"([^"]+)"', player_data)
                if url_match:
                    video_url = url_match.group(1)
                    print(f"直接提取到url: {video_url}")
                    
                    # 清理URL
                    if '\\/' in video_url:
                        video_url = video_url.replace('\\/', '/')
                    
                    # 确保是完整URL
                    if not video_url.startswith('http'):
                        if video_url.startswith('//'):
                            video_url = 'https:' + video_url
                        elif video_url.startswith('/'):
                            video_url = self.host + video_url
                    
                    return video_url
            
            # 在整个HTML中查找url字段
            url_match = re.search(r'"url"\s*:\s*"([^"]+)"', html)
            if url_match:
                video_url = url_match.group(1)
                print(f"从HTML提取到url: {video_url}")
                
                if '\\/' in video_url:
                    video_url = video_url.replace('\\/', '/')
                
                if not video_url.startswith('http'):
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    elif video_url.startswith('/'):
                        video_url = self.host + video_url
                
                return video_url
            
            # 查找视频链接
            video_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
            ]
            
            for pattern in video_patterns:
                match = re.search(pattern, html)
                if match:
                    video_url = match.group(1)
                    print(f"找到视频链接: {video_url}")
                    return video_url
            
        except Exception as e:
            print(f"提取视频地址失败: {e}")
        
        print(f"未能提取到视频地址，返回原始地址")
        return play_url
    
    def is_test_video(self, text):
        """
        检查是否是测试视频
        """
        if not text:
            return False
            
        text_lower = text.lower()
        
        # 测试视频特征
        test_patterns = [
            'oplist.wya6.cn',
            'web.wya6.com',
            'k0udeyaayccydz.djvod.ndcimgs.com',
            'pan.baidu.re',
            'test.mp4', 'demo.mp4', 'sample.mp4',
            'short.mp4', 'preview.mp4', 'trailer.mp4',
            'ad.mp4', '广告.mp4',
            '/10秒.mp4', '/15秒.mp4', '/30秒.mp4',
            '/10s.mp4', '/15s.mp4', '/30s.mp4',
            'error.html', '404.mp4', 'error.mp4',
        ]
        
        for pattern in test_patterns:
            if pattern in text_lower:
                print(f"检测到测试视频特征: {pattern}")
                return True
                
        return False

    def localProxy(self, param):
        try:
            if 'wdict' in param:
                wdict = json.loads(self.d64(param['wdict']))
                url = f"{wdict['jx']}{wdict['id']}"
                return [302, 'text/html', None, {'Location': url}]
            else:
                return [500, 'text/html', '缺少参数']
        except Exception as e:
            print(f"代理请求失败: {str(e)}")
            return [500, 'text/html', f'代理请求失败: {str(e)}']

    def liveContent(self, url):
        pass

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""