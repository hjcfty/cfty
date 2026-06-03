var rule = {
author: '小可乐/v5.12.1',
title: '骚火电影VIP',
类型: '影视',
//host: 'https://saohuo.tv',
host: 'http://shapp.us',
hostJs: 'HOST = pdfh(fetch(HOST), "ul&&a:eq(0)&&href")',
headers: {
    'User-Agent': MOBILE_UA,
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
},
编码: 'utf-8',
timeout: 10000,

homeUrl: '/',
url: '/list/fyfilter-fypage.html',
filter_url: '{{fl.cateId or "fyclass"}}',
searchUrl: '/s-**---------fypage.html',
detailUrl: '',

limit: 9,
double: false,
class_name: '电影&剧集&综艺&动漫&理论',
class_url: '1&2&3&4&5',

推荐: '*',
一级: $js.toString(() => {
    VODS = [];
    let klists = pdfa(fetch(input), '.v_img');
    klists.forEach(it => {
        let kname = pdfh(it, 'a&&title')?.trim() || '名称';
        let kpic = pdfh(it, 'img&&data-original')?.trim() || '图片';
        let kremarks = pdfh(it, '.v_note&&Text')?.trim() || '状态';
        let kid = pdfh(it, 'a&&href')?.trim() || 'Id';
        VODS.push({
            vod_name: kname,
            vod_pic: kpic,
            vod_remarks: kremarks,
            vod_id: `${kid}@${kname}@${kpic}@${kremarks}`
        });
    });   
}),
搜索: '*',
二级: $js.toString(() => {
    let [kid, knane, kpic, kremarks] = input.split('@');
    let khtml = fetch(kid);
    let intros = pdfh(khtml, '.v_info_box&&p--a&&Text').split('/').reverse();
    let ktabs = pdfa(khtml, '.from_list&&li').map(it => { return pdfh(it, 'body&&Text'); });
    let kurls = pdfa(khtml, '#play_link&&li').map(item => {
        let kurl = pdfa(item, 'body&&a').reverse().map(it => { return pdfh(it, 'a&&Text') + '$' + pd(it, 'a&&href', HOST); });
        return kurl.join('#');
    });
    if (!ktabs.length || !kurls.length) {
        ktabs = ['暂无线路'];
        kurls = ['暂无播放源$ '];
    }
    VOD = {
        vod_id: kid,
        vod_name: knane,
        vod_pic: kpic,
        type_name: /20|19/.test(intros[2]) ? '类型' : intros[2],
        vod_remarks: kremarks,
        vod_year: /20|19/.test(intros[2]) ? intros[2].trim() : intros[3].trim(),
        vod_area: /20|19/.test(intros[2]) ? intros[3] : intros[4],
        vod_lang: '语言',
        vod_director: intros[1].replace('导演:',''),
        vod_actor: intros[0].replace('主演:',''),
        vod_content: pdfh(khtml, '.p_txt&&Text'),
        vod_play_from: ktabs.join('$$$'),
        vod_play_url: kurls.join('$$$')
    };
}),

play_parse: true,
lazy: $js.toString(() => {
    let kp = 0, kurl = input, headers = {'User-Agent': MOBILE_UA};
    let jurl = pdfh(fetch(kurl), 'iframe&&src');
    let furl = jurl.split('/index')[0];
    let url, t, key;
    let kcode = pdfh(fetch(jurl), 'body&&script&&Html').split('var act')[0].split('function OKOK')[1].replace(/var /g, '');
    eval('function OKOK'+kcode);
    let rbody = `url=${url}&t=${t}&key=${key}&act=0&play=1`;
    let khtml = fetch(`${furl}/api.php`, {
        headers: {
            ...rule.headers,
            'Referer': jurl,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        },
        body: rbody,
        method: 'POST'
    });
    kurl = rule.safeParseJSON(khtml)?.url ?? '';
    kurl = /^http/.test(kurl) ? kurl : `${furl}${kurl}`;
    if (!/m3u8|mp4|mkv/.test(kurl)) {
        kp = 1;
        kurl = jurl;
    }
    input = { jx: 0, parse: kp, url: kurl, header: headers };
}),

safeParseJSON: function(jStr){
    try {return JSON.parse(jStr);} catch(e) {return null;}
},

filter: 'H4sIAAAAAAAAA6XUO08CQRAH8P4+xtYUHByClnYkJjbGhlgQpfJRqYkhJOgF5ZEoGMUX8ojiIQKCJgZP0S/D7t59C894w4wGK8r9XTK789+diytMZTMRJc5WYztshi1HN2PhFeZhG9H1mLOWvTdezjnr7ejalgORONtwmKcatt74ZmehsoTH5WKJZwyXp0Ys0z2hp1wOjljs5kWy6HIIi2Qbw0HJ5WksYhT46xts6cUq6fOhmQHHs8jsoxw0wX20vDwZ1fGj1w9IfQ09Y+Dh1QD6/rF9cQ+OzYq9liwWwEm3elbsXYKTdlMvvKODO/0uJZQlj8J8k14LafnWsC/2gTG6hcVZQMzNrtzjHfqwiPw4JI65ibM6cczNyvWIk9yOusSnxufgC2IOoYmDwLBlqTI0TWkk4RO+LzuZQfd7ad/2TQVcJX2nRL8PjjmJ3sAa3IFjTlbn0+qmwTEnaTZ5pwyOOYl8WbbgHfn/ycmPOWmTxqT9s3WIDGzOGWVwMpp626pBdBoZzeq7KJ6Bq7+eUrfA68/wCdOz2yfi+RScvLKS6Qw6ODlqtcav2uCY3tB84u08OPkVPdStx2vw4Php1v4+GHBseW5+LuxqwDv+bgLqz90oiS/ZAX9cZQUAAA=='
}