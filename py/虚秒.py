#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import sys
import re
import time
import os
import hashlib
from collections import defaultdict
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "我的直播订阅"
    
    def init(self, extend=""):
        print("我的直播订阅初始化")
        self.base_url = "http://ty.xwsbm.top/php2/mytv_proxy.php?action=universal_custom&id=xw_xmtx&password=7878778"
        self.channel_configs = {}
        self.cache_time = 300
        self.last_update = 0
        self.cached_data = None
        self.line_url_to_name = {}
        
    def homeContent(self, filter):
        result = {}
        
        current_time = time.time()
        if self.cached_data and current_time - self.last_update < self.cache_time:
            return self.cached_data
            
        try:
            response = requests.get(self.base_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code == 200 and response.text.strip():
                content = response.text
                data = json.loads(content)
                
                classes = []
                if 'lives' in data:
                    for live in data['lives']:
                        class_name = re.sub(r'[🔐🔑🌏]', '', live.get('name', '未知分类')).strip()
                        url = live.get('url', '')
                        
                        self.line_url_to_name[url] = class_name
                        
                        if url.startswith('file://'):
                            url = url.replace('file://', '/storage/emulated/0/')
                            print(f"转换本地文件路径: {live.get('url')} -> {url}")
                        
                        classes.append({
                            'type_name': class_name,
                            'type_id': url
                        })
                
                local_sub_file = "/storage/emulated/0/TV/path_list.txt"
                if os.path.exists(local_sub_file):
                    local_classes = self.load_local_subscriptions(local_sub_file)
                    for local_class in local_classes:
                        self.line_url_to_name[local_class['type_id']] = local_class['type_name']
                    classes.extend(local_classes)
                
                result['class'] = classes
                self.cached_data = result
                self.last_update = current_time
                return result
                
        except Exception as e:
            print(f"获取分类错误: {e}")
        
        result['class'] = []
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        
        try:
            content = self.get_source_content(tid)
            
            if content:
                is_m3u, is_txt = self.debug_format_detection(tid, content)
                
                if is_m3u:
                    groups = self.parse_m3u_groups(content)
                elif is_txt:
                    groups = self.parse_txt_groups(content)
                else:
                    groups = self.parse_m3u_groups(content)
                
                page_size = 90
                group_list = list(groups.items())
                total_groups = len(group_list)
                total_pages = (total_groups + page_size - 1) // page_size
                
                start_idx = (int(pg) - 1) * page_size
                end_idx = start_idx + page_size
                current_groups = group_list[start_idx:end_idx]
                
                vod_list = []
                for group_name, group_info in current_groups:
                    line_name = self.get_line_name_from_url(tid)
                    icon = self.get_group_icon(line_name, group_name)
                    
                    vod_info = {
                        'vod_id': f"{tid}||{group_name}",
                        'vod_name': group_name,
                        'vod_pic': icon,
                        'vod_remarks': f"{group_info['count']}个频道",
                    }
                    vod_list.append(vod_info)
                
                result['list'] = vod_list
                result['page'] = int(pg)
                result['pagecount'] = total_pages
                result['limit'] = page_size
                result['total'] = total_groups
                return result
        
        except Exception as e:
            print(f"获取分类内容错误: {e}")
        
        result['list'] = []
        return result

    def detailContent(self, ids):
        """详情页面 - 线路位置显示线路，选集位置显示频道"""
        vod_id = ids[0]
        
        try:
            if '||' in vod_id:
                line_url, group_name = vod_id.split('||', 1)
            else:
                line_url = vod_id
                group_name = '默认分组'
            
            content = self.get_source_content(line_url)
            
            if content:
                is_m3u, is_txt = self.debug_format_detection(line_url, content)
                
                if is_m3u:
                    channels_data = self.parse_m3u_channels_grouped(content, group_name)
                elif is_txt:
                    channels_data = self.parse_txt_channels_grouped(content, group_name)
                else:
                    channels_data = self.parse_m3u_channels_grouped(content, group_name)
                
                if not channels_data:
                    line_name = self.get_line_name_from_url(line_url)
                    return {'list': [{
                        'vod_id': vod_id,
                        'vod_name': group_name,
                        'vod_pic': self.get_group_icon(line_name, group_name),
                        'vod_remarks': '该分组暂无频道',
                    }]}
                
                # 构建播放源和播放URL
                play_from = []  # 线路位置显示线路
                play_url = []   # 选集位置显示频道
                
                # 按线路分组
                max_lines = 0
                for channel_info in channels_data.values():
                    max_lines = max(max_lines, len(channel_info['urls']))
                
                # 每条线路包含所有频道
                for line_num in range(1, max_lines + 1):
                    channel_items = []
                    for channel_name, channel_info in channels_data.items():
                        if len(channel_info['urls']) >= line_num:
                            line_info = channel_info['urls'][line_num - 1]
                            url = line_info['url']
                            config_key = line_info['config_key']
                            
                            channel_item = f"{channel_name}${url}"
                            if config_key:
                                channel_item += f"@@@{config_key}"
                            channel_items.append(channel_item)
                    
                    if channel_items:
                        play_from.append(f"线路{line_num}")
                        play_url.append("#".join(channel_items))
                
                line_name = self.get_line_name_from_url(line_url)
                result = {
                    'list': [{
                        'vod_id': vod_id,
                        'vod_name': f"{line_name} - {group_name}",
                        'vod_pic': self.get_group_icon(line_name, group_name),
                        'vod_remarks': f"共{len(channels_data)}个频道",
                        'vod_play_from': "$$$".join(play_from),  # 线路位置显示线路
                        'vod_play_url': "$$$".join(play_url)     # 选集位置显示频道
                    }]
                }
                return result
                    
        except Exception as e:
            print(f"详情页面错误: {e}")
            import traceback
            traceback.print_exc()
        
        return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        try:
            if '@@@' in id:
                url_part, config_key = id.split('@@@', 1)
            else:
                url_part = id
                config_key = None
            
            if '$' in url_part:
                clean_url = url_part.split('$')[1]
            else:
                clean_url = url_part
            
            result = {
                'parse': 0,
                'url': clean_url
            }
            
            if config_key and config_key in self.channel_configs:
                config = self.channel_configs[config_key]
                headers = config.get('headers', {})
                if headers:
                    result['header'] = json.dumps(headers)
                
                drm = config.get('drm', {})
                if drm:
                    result.update(drm)
            
            return result
            
        except Exception as e:
            print(f"播放内容错误: {e}")
        
        return {'parse': 0, 'url': ''}

    # 以下是您原来的辅助方法，保持不变
    def load_local_subscriptions(self, file_path):
        classes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            for line in lines:
                if not line or line.startswith('#'):
                    continue
                
                if '|' in line:
                    name, path = line.split('|', 1)
                    name = name.strip()
                    path = path.strip()
                else:
                    name = os.path.basename(line).replace('.m3u', '').replace('.txt', '')
                    path = line.strip()
                
                if path.startswith('/') and not os.path.exists(path):
                    print(f"警告: 本地文件不存在: {path}")
                    continue
                
                classes.append({
                    'type_name': name,
                    'type_id': path
                })
                print(f"添加本地分类: {name} -> {path}")
                
        except Exception as e:
            print(f"加载本地订阅错误: {e}")
            
        return classes

    def get_line_name_from_url(self, line_url):
        for url, name in self.line_url_to_name.items():
            if url in line_url:
                return name
        
        if line_url.startswith('/storage/emulated/0/'):
            filename = os.path.basename(line_url)
            return f"本地{filename.replace('.m3u', '').replace('.txt', '')}"
        
        return '默认线路'

    def get_group_icon(self, line_name, group_name):
        """获取分组图标 - 保持您原来的配置"""
        
        # 虚秒直播线路配置
        if line_name == '⚡虚秒直播':
            if '🔊超清频道' in group_name:
                return 'https://pastebin.880223.xyz/~car1'
            elif '🔊央视精品' in group_name:
                return 'https://pastebin.880223.xyz/~car2'  
            elif '🔊央视特线' in group_name:
                return 'https://pastebin.880223.xyz/~car6'  
            elif '🔊卫视特线' in group_name:
                return 'https://pastebin.880223.xyz/~car4'  
            elif '🔊央视秒播' in group_name:
                return 'https://pastebin.880223.xyz/~car5'  
            elif '🔊卫视秒播' in group_name:
                return 'https://pastebin.880223.xyz/~car3'  
            elif '🔊央视高码' in group_name:
                return 'https://pastebin.880223.xyz/~car7'  
            elif '🔊卫视高码' in group_name:
                return 'https://pastebin.880223.xyz/~car8'  
            elif '🔊央视官方' in group_name:
                return 'https://pastebin.880223.xyz/~car9'  
            elif '🔊卫视官方' in group_name:
                return 'https://pastebin.880223.xyz/~car10'  
            elif '🔊央视高清' in group_name:
                return 'https://pastebin.880223.xyz/~car11'  
            elif '🔊卫视高清' in group_name:
                return 'https://pastebin.880223.xyz/~car12'  
            elif '🔊央视咪咕' in group_name:
                return 'https://pastebin.880223.xyz/~car13'  
            elif '🔊卫视咪咕' in group_name:
                return 'https://pastebin.880223.xyz/~car14'  
            elif '🔊央视推流' in group_name:
                return 'https://pastebin.880223.xyz/~car15'  
            elif '🔊卫视推流' in group_name:
                return 'https://pastebin.880223.xyz/~car16'  
            elif '🔊央视备用' in group_name:
                return 'https://pastebin.880223.xyz/~car17'  
            elif '🔊卫视备用' in group_name:
                return 'https://pastebin.880223.xyz/~car18'  
            elif '🔊广东频道' in group_name:
                return 'https://pastebin.880223.xyz/~car19'  
            elif '🔊浙江频道' in group_name:
                return 'https://pastebin.880223.xyz/~car21'
            else:
                return 'https://car.zntv.dpdns.org'# 跑车豪车
        
        # 港台直播线路配置
        if line_name == '🇭🇰港台直播':
            if '🔊凤凰频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj1'
            elif '🔊翡翠明珠' in group_name:
                return 'https://pastebin.880223.xyz/~zdj2'  
            elif '🔊无线频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj3'  
            elif '🔊影视频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj4'  
            elif '🔊HOY频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj5'  
            elif '🔊NOW频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj6'  
            elif '🔊RHK频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj7'  
            elif '🔊VIU频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj8'  
            elif '🔊中台华民' in group_name:
                return 'https://pastebin.880223.xyz/~zdj9'  
            elif '🔊东森龙华' in group_name:
                return 'https://pastebin.880223.xyz/~zdj10'  
            elif '🔊体育频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj11'  
            elif '🔊澳门频道' in group_name:
                return 'https://pastebin.880223.xyz/~zdj12'  
            else:
                return 'https://car.zntv.dpdns.org'# 跑车豪车
        
        # 虚无直播线路配置
        if line_name == '🌋虚无直播':
            if '📡虚无超清' in group_name:
                return 'https://pastebin.880223.xyz/~zgwd'
            elif '📡虚无央视' in group_name:
                return 'https://pastebin.880223.xyz/~dffs'  
            elif '📡虚无卫视' in group_name:
                return 'https://pastebin.880223.xyz/~DF5C'  
            elif '📡虚无咪咕' in group_name:
                return 'https://pastebin.880223.xyz/~JLXL'  
            elif '📡虚无移动' in group_name:
                return 'https://pastebin.880223.xyz/~DF5C1'  
            elif '📡虚无组播' in group_name:
                return 'https://pastebin.880223.xyz/~DF5CP'  
            elif '📡虚无酒店' in group_name:
                return 'https://pastebin.880223.xyz/~DF61'  
            elif '📡虚无精品' in group_name:
                return 'https://pastebin.880223.xyz/~DF61P'  
            elif '📡虚无剧场' in group_name:
                return 'https://pastebin.880223.xyz/~DF5B'  
            elif '📡虚无两广' in group_name:
                return 'https://pastebin.880223.xyz/~DF5BP'  
            elif '📡虚无港台' in group_name:
                return 'https://pastebin.880223.xyz/~DF41'  
            elif '📡虚无斯玛' in group_name:
                return 'https://pastebin.880223.xyz/~DF41P'  
            elif '📡虚无解说' in group_name:
                return 'https://pastebin.880223.xyz/~DF31AG'  
            elif '📡虚无轮播' in group_name:
                return 'https://pastebin.880223.xyz/~DF31BJ'  
            elif '📡虚无赛事' in group_name:
                return 'https://pastebin.880223.xyz/~DF27'  
            elif '📡虚无歌曲' in group_name:
                return 'https://pastebin.880223.xyz/~DF17'  
            elif '📡虚无电台' in group_name:
                return 'https://pastebin.880223.xyz/~JL3'  
            elif '📡虚无春晚' in group_name:
                return 'https://pastebin.880223.xyz/~JL1'  
            else:
                return 'http://xw.osfs.top/index.php'# 大国重器
        
        # 王子直播线路配置
        if line_name == '🤴王子直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://img-api.wuxie.de/bing/random'# bing风景     
        
        # 简单直播线路配置
        if line_name == '🌀简单直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://car.zntv.dpdns.org'# 豪车
        
        # 咪咕直播线路配置
        if line_name == '🍄咪咕直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://img.catvod.com'# 猫家风景
        
        # 日后直播线路配置
        if line_name == '☀日后直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://imgapi.cn/api.php?fl=fengjing&gs=images'# IMG风景             
        
        # 长城直播线路配置
        if line_name == '🧱长城直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://picsum.photos/1080/'# 随机风景
         
        # 裤佬直播线路配置
        if line_name == '🩳裤佬直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列1'# 樱道风景1
                
        # 视家直播线路配置
        if line_name == '📹视家直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列2'# 樱道风景2
        
        # 风云直播线路配置
        if line_name == '🌩风云直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列3'# 樱道风景3
        
        # 港台大陆线路配置
        if line_name == '🌅港台大陆':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列4'# 樱道风景4
        
        # 杰克直播线路配置
        if line_name == '🛩杰克直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列5'# 樱道风景5
        
        # 斯玛直播线路配置
        if line_name == '🎠斯玛直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列6'# 樱道风景6
        
        # 苏影直播线路配置
        if line_name == '🌟苏影直播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列7'# 樱道风景7
        
        # 虎牙轮播线路配置
        if line_name == '🐯虎牙轮播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://cdn.seovx.com/d/?mom=302'# 二次元
        
        # 斗鱼轮播线路配置
        if line_name == '🐠斗鱼轮播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.mtyqx.cn/tapi/random.php'# 二次元1
        
        # 歪歪轮播线路配置
        if line_name == '🦑歪歪轮播':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://www.hhlqilongzhu.cn/api/tu_yitu.php'# 随机动漫
        
                # 经典歌曲线路配置
        if line_name == '🎸经典歌曲':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列8'# 樱道风景8
        
        # 聚合体育线路配置
        if line_name == '🏀聚合体育':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列9'# 樱道风景9
        
        # 荟萃电影线路配置
        if line_name == '📽荟萃电影':
            if '实际名字' in group_name:
                return ''
            elif '名字' in group_name:
                return ''  
            elif '名字' in group_name:
                return ''  
            else:
                return 'https://api.r10086.com/樱道随机图片api接口.php?图片系列=风景系列10'# 樱道风景10
        
        # 全局默认配置最低优先级
        else:
            if '🌋虚无直播' in group_name:
                return 'http://xw.osfs.top/index.php'
            elif '关键字' in group_name:
                return ''
            elif '关键字' in group_name:
                return ''
            elif '关键字' in group_name:
                return ''
            else:
                return 'https://car.zntv.dpdns.org'# 赛车

    def get_source_content(self, source):
        try:
            if source.startswith('/storage/emulated/0/'):
                return self.read_local_file_absolute(source)
            else:
                response = requests.get(source, timeout=15)
                response.encoding = 'utf-8'
                return response.text if response.status_code == 200 else None
        except Exception as e:
            print(f"获取源内容错误: {e}")
            return None

    def read_local_file_absolute(self, file_path):
        try:
            if os.path.exists(file_path):
                encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue
            return None
        except Exception as e:
            print(f"读取本地文件错误: {e}")
            return None

    def debug_format_detection(self, source, content=None):
        is_m3u = self.is_m3u_format(source, content)
        is_txt = self.is_txt_format(source) or (content and self.looks_like_txt_content(content))
        return is_m3u, is_txt

    def is_m3u_format(self, source, content=None):
        m3u_extensions = ['.m3u', '.m3u8']
        source_lower = source.lower()
        
        for ext in m3u_extensions:
            if ext in source_lower:
                return True
        
        if content:
            lines = content.split('\n')
            extinf_count = 0
            total_lines = min(20, len(lines))
            
            for i in range(total_lines):
                line = lines[i].strip()
                if line.startswith('#EXTM3U'):
                    return True
                if line.startswith('#EXTINF:'):
                    extinf_count += 1
            
            if extinf_count > total_lines * 0.3:
                return True
        
        return False

    def is_txt_format(self, source):
        txt_extensions = ['.txt', '.nzk', '.tv', '.live']
        source_lower = source.lower()
        return any(ext in source_lower for ext in txt_extensions)

    def looks_like_txt_content(self, content):
        if not content:
            return False
        
        lines = content.split('\n')
        txt_like_count = 0
        total_lines = min(10, len(lines))
        
        for i in range(total_lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                continue
            if ',' in line or '#' in line or 'http' in line:
                txt_like_count += 1
        
        return txt_like_count > total_lines * 0.5

    def parse_m3u_groups(self, m3u_content):
        groups = {}
        lines = m3u_content.split('\n')
        current_info = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('#EXTINF:'):
                current_info = self.parse_extinf(line)
                
            elif line and not line.startswith('#') and current_info:
                group_name = current_info.get('group', '默认分组')
                
                if group_name not in groups:
                    groups[group_name] = {
                        'name': group_name,
                        'count': 0,
                        'logo': current_info.get('logo', self.get_group_icon('', group_name))
                    }
                groups[group_name]['count'] += 1
                current_info = {}
        
        return groups

    def parse_txt_groups(self, txt_content):
        groups = {}
        lines = txt_content.split('\n')
        current_group = '默认分组'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if '#genre#' in line:
                group_name = line.split(',')[0].replace('#genre#', '').strip()
                if group_name:
                    current_group = group_name
                    if current_group not in groups:
                        groups[current_group] = {
                            'name': current_group,
                            'count': 0,
                            'logo': self.get_group_icon('', current_group)
                        }
                continue
                
            channel_info = self.parse_txt_channel_line(line)
            if channel_info:
                if current_group not in groups:
                    groups[current_group] = {
                        'name': current_group,
                        'count': 0,
                        'logo': self.get_group_icon('', current_group)
                    }
                groups[current_group]['count'] += 1
        
        if not groups:
            groups = self.create_default_group_from_content(txt_content)
        
        return groups

    def create_default_group_from_content(self, content):
        groups = {}
        channel_count = 0
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if 'http' in line and not line.startswith('#'):
                channel_count += 1
        
        if channel_count > 0:
            groups['所有频道'] = {
                'name': '所有频道',
                'count': channel_count,
                'logo': self.get_group_icon('', '所有频道')
            }
        
        return groups

    def parse_txt_channel_line(self, line):
        info = {}
        
        if not line or line.startswith('#') or '#genre#' in line:
            return None
        
        if ',' in line:
            parts = [part.strip() for part in line.split(',')]
            if len(parts) >= 2:
                if parts[1].startswith(('http', 'rtmp', 'rtsp')):
                    info['name'] = parts[0]
                    info['url'] = parts[1]
                elif len(parts) >= 3 and parts[2].startswith(('http', 'rtmp', 'rtsp')):
                    info['name'] = parts[1]
                    info['url'] = parts[2]
                elif len(parts) >= 3 and parts[1].startswith(('http', 'rtmp', 'rtsp')):
                    info['name'] = parts[0]
                    info['url'] = parts[1]
                
        elif '#' in line:
            parts = [part.strip() for part in line.split('#')]
            if len(parts) >= 2 and parts[1].startswith(('http', 'rtmp', 'rtsp')):
                info['name'] = parts[0]
                info['url'] = parts[1]
        
        elif 'http' in line:
            parts = re.split(r'\s+', line, 1)
            if len(parts) >= 2 and parts[1].startswith(('http', 'rtmp', 'rtsp')):
                info['name'] = parts[0]
                info['url'] = parts[1]
            else:
                http_index = line.find('http')
                if http_index > 0:
                    info['name'] = line[:http_index].strip()
                    info['url'] = line[http_index:].strip()
        
        return info if info.get('name') and info.get('url') else None

    def parse_extinf(self, extinf_line):
        info = {}
        
        if ',' in extinf_line:
            name = extinf_line.split(',')[-1].strip()
            name = re.sub(r'^["\']|["\']$', '', name)
            if name and len(name) > 1:
                info['name'] = name
            else:
                info['name'] = '未知频道'
        else:
            info['name'] = '未知频道'
        
        group_match = re.search(r'group-title="([^"]*)"', extinf_line)
        info['group'] = group_match.group(1) if group_match else '默认分组'
            
        logo_match = re.search(r'tvg-logo="([^"]*)"', extinf_line)
        if logo_match:
            info['logo'] = logo_match.group(1)
            
        return info

    def parse_m3u_channels_grouped(self, m3u_content, target_group):
        channels = {}
        lines = m3u_content.split('\n')
        current_config = []
        current_name = "未知频道"
        current_group = ""
        
        for i in range(len(lines)):
            line = lines[i].strip()
            if not line:
                continue
                
            if line.startswith('#EXTINF:'):
                current_config = [line]
                current_name = self.extract_channel_name_simple(line)
                
                group_match = re.search(r'group-title="([^"]*)"', line)
                current_group = group_match.group(1) if group_match else '默认分组'
                
            elif line.startswith('#') and current_config:
                current_config.append(line)
                
            elif line and not line.startswith('#') and current_config and (current_group == target_group or target_group == '所有频道'):
                url = line
                
                logo_match = re.search(r'tvg-logo="([^"]*)"', ' '.join(current_config))
                logo = logo_match.group(1) if logo_match else None
                
                if current_name not in channels:
                    channels[current_name] = {
                        'name': current_name,
                        'logo': logo,
                        'urls': []
                    }
                
                config = self.parse_config_lines(current_config)
                config_key = f"config_{self.generate_config_key(url)}" if config else None
                
                if config_key and config:
                    self.channel_configs[config_key] = config
                
                channels[current_name]['urls'].append({
                    'url': url,
                    'config': config,
                    'config_key': config_key,
                    'line_number': len(channels[current_name]['urls']) + 1
                })
                
                current_config = []
                current_name = "未知频道"
                current_group = ""
        
        return channels

    def parse_txt_channels_grouped(self, txt_content, target_group):
        channels = {}
        lines = txt_content.split('\n')
        current_group = '默认分组'
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '#genre#' in line:
                group_name = line.split(',')[0].replace('#genre#', '').strip()
                if group_name:
                    current_group = group_name
                continue
                
            channel_info = self.parse_txt_channel_line(line)
            if channel_info and (current_group == target_group or target_group == '所有频道'):
                channel_name = channel_info['name']
                url = channel_info['url']
                
                if channel_name not in channels:
                    channels[channel_name] = {
                        'name': channel_name,
                        'logo': None,
                        'urls': []
                    }
                
                config_key = f"config_{self.generate_config_key(url)}"
                channels[channel_name]['urls'].append({
                    'url': url,
                    'config': None,
                    'config_key': config_key,
                    'line_number': len(channels[channel_name]['urls']) + 1
                })
        
        return channels

    def generate_config_key(self, url):
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:8]

    def extract_channel_name_simple(self, extinf_line):
        if ',' in extinf_line:
            name = extinf_line.split(',')[-1].strip()
            name = re.sub(r'^["\']|["\']$', '', name)
            if name and len(name) > 1:
                return name
        
        tvg_match = re.search(r'tvg-name="([^"]*)"', extinf_line)
        if tvg_match:
            return tvg_match.group(1)
        
        return "未知频道"

    def parse_config_lines(self, config_lines):
        config = {
            'headers': {},
            'drm': {}
        }
        
        for line in config_lines:
            line = line.strip()
            if not line:
                continue
                
            if 'user-agent=' in line.lower():
                ua_match = re.search(r'user-agent="([^"]*)"', line, re.IGNORECASE)
                if ua_match:
                    config['headers']['User-Agent'] = ua_match.group(1)
            
            elif 'stream_headers=' in line.lower():
                headers_match = re.search(r'stream_headers="([^"]*)"', line, re.IGNORECASE)
                if headers_match:
                    headers_str = headers_match.group(1)
                    for header_part in headers_str.split('&'):
                        if '=' in header_part:
                            key, value = header_part.split('=', 1)
                            config['headers'][key] = value
        
        return config if config['headers'] else None

    def searchContent(self, key, quick, pg="1"):
        return {'list': []}

    def localProxy(self, param):
        return {}