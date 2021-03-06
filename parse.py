#!/usr/local/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import re
import codecs
import traceback
import logging
import json
import collections
import optparse

import sementic

basic_data = {}
heteronym_data = collections.defaultdict(list)

pos_map = dict(
        fed3=u'名',
        fed4=u'動',
        fed5=u'形',
        fed6=u'副',
        fed7=u'助',
        fed8=u'介',
        fed9=u'嘆',
        feda=u'連',
        fee0=u'代',
        )
pos_map['97e3']=u'綴'
pos_map['967b']=u'狀'
pos_map['97d6']=u'辨'
pos_map['97d5']=u'似'

number_map = dict(map(unicode.split, u'''
fe52 <1>
fe53 <2>
fe54 <3>
fe55 <4>
fe56 <5>
fe57 <6>
fe58 <7>
fe59 {1}
fe5a {2}
fe5b {3}
fe5c {4}
fe5d {5}
fe5e {6}
fe5f {7}
fe60 {8}
fe61 {9}
fe62 {10}
fe63 {11}
fe64 {12}
fe65 {13}
fe66 {14}
fe67 {15}
98bd {16}
98be {17}
98bf {18}
98c0 {19}
'''.strip().splitlines()))

phonetone_map = dict(map(unicode.split, u'''
#fe68 ａ1
#fe69 ａ2
#fe6a ａ3
#fe6b ａ4
#fe6c ｅ1
#fe6d ｅ2
#fe6e ｅ3
#fe6f ｅ4
#fe70 ｉ1
#fe71 ｉ2
#fe72 ｉ3
#fe73 ｉ4
#fe74 ｏ1
#fe75 ｏ2
#fe76 ｏ3
#fe77 ｏ4
#fe7c ｕ1
#fe7d ｕ2
#fe7e ｕ3
#fea1 ｕ4
#fe78 ｒ1
#fe79 ｒ2
#fe7a ｒ3
#fe7b ｒ4
#fea2 ｚ1
#fea3 ｚ2
#fea4 ｚ3
#fea5 ｚ4
#95a2 ｓ2
#9ce0 ａ1
#9ce1 ａ2
#9ce2 ａ3
#9ce3 ａ4
#9ce4 g
fe68 ā
fe69 á
fe6a ǎ
fe6b à
fe6c ē
fe6d é
fe6e ě
fe6f è
fe70 ī
fe71 í
fe72 ǐ
fe73 ì
fe74 ō
fe75 ó
fe76 ǒ
fe77 ò
fe7c ū
fe7d ú
fe7e ǔ
fea1 ù
fe78 r̄
fe79 ŕ
fe7a ř
fe7b r̀
fea2 z̄
fea3 ź
fea4 ž
fea5 z̀
9ce0 ā
9ce1 á
9ce2 ǎ
9ce3 à
9ce4 g
97f6 a
9bcd ǖ
9bce ǘ
9bcf ǚ
9bd0 ǜ
97e7 ü
9bd4 ề
'''.strip().splitlines()))

re_char = r'(?:.|\{\[....\]\})'

bpmf0 = u'˙'
bpmf1 = u'ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙ'
bpmf2 = u'ㄧㄨㄩ'
bpmf3 = u'ㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ'
bpmf4 = u'ˇˊˋ'
re_bpmf = u'[%s%s%s%s%s]' % (bpmf0, bpmf1, bpmf2, bpmf3, bpmf4)

normal_map = {}

def setup_logging():
    formatter = logging.Formatter('%(levelname)-8s [%(asctime)s %(filename)s:%(lineno)s] %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    sh = logging.StreamHandler(codecs.getwriter('utf8')(sys.stderr))
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    fh = logging.FileHandler('parse.log', mode='w', encoding='utf8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def build_normal_map():
    for i in range(26):
        normal_map[0xff21+i] = unichr(ord(u'A')+i)
        normal_map[0xff41+i] = unichr(ord(u'a')+i)
    normal_map[ord(u'｜')] = u'ㄧ'
    normal_map[ord(u'　')] = u' '
    normal_map[ord(u'､')] = u'、'

def strip(html):
    html = html.strip()
    m = re.search(ur'^(&nbsp;)*(.*?)(&nbsp;)*$', html)
    return m.group(2)

def parse_basic(title):
    m = re.search(ur'''(?P<title>.+?)  <span class="lable">部首</span> (?P<radical>.+?) <span class="lable">部首外筆畫</span> (?P<non_radical_stroke_count>\d+) <span class="lable">總筆畫</span> (?P<stroke_count>\d+)''', title)
    if m:
        return m.groupdict()

    m = re.search(ur'''\{\[fe50\]\}(?P<title>%s)\{\[fe51\]\}(?P<radical>%s)-(?P<non_radical_stroke_count>\d+)-(?P<stroke_count>\d+)''' % (re_char, re_char),
            title)
    if m:
        return m.groupdict()

    m = re.match(ur'''(?P<title>.+)''', title)
    if m:
        return m.groupdict()

    return dict(title=title)

def split_td(html):
    state = 0
    idx = 0
    result = ['']
    for x in re.split(ur'((?:</td>)|<td[^>]*>)', html):
        x = strip(x)
        if x == '':
            continue
        if x.startswith('<td'):
            if state == 0:
                state = 1
            else:
                idx += 1
                result.append('')
        elif x == '</td>':
            idx += 1
            result.append('')
            state = 0
        else:
            result[idx] += x
    while result and result[-1] == '':
        result.pop()
    return result

def parse_def(text, definition):
    """
    """
    try:
        classifies = []
        sentences = []
        for s in sementic.split_sentence(text):
            c = sementic.classify_sentence(s)
            classifies.append(c)
            sentences.append(s)
            logging.debug('classify %s: %s' % (c, s))

        if re.search(r'0[^0]+0', ''.join(map(str, classifies))):
            logging.warn('complex definition')
            return

        while classifies and classifies[-1] != 0:
            c = classifies.pop()
            s = sentences.pop()
            if c == 1:
                if 'example' not in definition:
                    definition['example'] = []
                definition['example'].insert(0, s)
            elif c == 2:
                if 'quote' not in definition:
                    definition['quote'] = []
                definition['quote'].insert(0, s)
            elif c == 3:
                if 'link' not in definition:
                    definition['link'] = []
                definition['link'].insert(0, s)

        definition['def'] = ''.join(sentences)

    except sementic.UnbalanceBrances:
        pass


def parse_defs(detail, d):
    detail = detail.strip()

    # workaround for definition index > 15
    detail = re.sub(
            ur'(?<!>)(\{(?:1[6-9])\})',
            r'</td></tr>\n><tr><td></td><td>\1</td><td>',
            detail)

    logging.debug('detail=%s' % repr(detail))
    #print 'detail=>', repr(detail)
    items = re.findall('<tr>(.+?)</tr>', detail)

    definitions = []
    pos = ''
    order = 0
    for item in items:
        if not item:
            continue
        result = split_td(item)
        logging.debug('result=%s' % result)
        #print result
        if len(result) == 1 and result[0] in pos_map.values():
            pos = result[0]
            continue
        if len(result) == 1 and result[0] == u'辨&nbsp似':
            pos = u'辨似'
            continue
        if len(result) == 3:
            assert result[0] == '' or result[0] in pos_map.values() or result[0] == '{[97d2]}'
            if result[0] in pos_map.values():
                pos = result[0]
            assert result[1] == '' or result[1] in number_map.values()
            order += 1
            text = result[2]
        elif len(result) == 2:
            assert result[0] == '' or result[0] in number_map.values() or result[0] == '{[97d2]}'
            order += 1
            text = result[1]
        else:
            assert len(result) == 1
            text = result[0]
            assert not re.match(ur'^\{\[....\]\}$', text)
            order += 1

        definition = { 'def': text }
        if pos:
            definition['type'] = pos
        #definition['order'] = order

        parse_def(definition['def'], definition)

        #print 'result', result
        #for i, x in enumerate(result):
        #    print i, x
        definitions.append(definition)
    #print definitions
    return definitions

def associate_to_defs(key, data, defs):
    text = data[key]
    if text:
        logging.debug('associate_to_defs %s: %s' % (key, text))
        text = re.sub(r'\{(\d{1,2})\}', r'(\1)', text)
    while text:
        m = re.match(ur'^((?:\(\d+\))*)([^()]+)', text)
        if not m:
            logging.error('bad syntax %s: %s' % (key, text))
            return
        v = m.group(2).replace(u'、', u',').strip()
        text = text[len(m.group()):]

        if m.group(1) == '':
            defs[0][key] = v
        else:
            for num in re.findall(ur'\((\d+)\)', m.group(1)):
                idx = int(num)
                if not 1 <= idx <= len(defs):
                    logging.error('index out of bound')
                    return
                if key in defs[idx-1]:
                    defs[idx-1][key] += ',' + v
                else:
                    defs[idx-1][key] = v



def parse_heteronym(html):
    m = re.search(
    ur'''<table width="90%" border="1" cellspacing="1" cellpadding="1">
  <tr>
    <td colspan="2">&nbsp;(\d+)\.　(?P<titledata>.*?)</td>
  </tr>
  <tr>
    <td colspan="2" width="100%">&nbsp;<span class="lable">注音一式</span>(?P<bopomofo>.*?)</td></tr><tr>
    <td width="50%">&nbsp;<span class="lable">漢語拼音</span>(?P<pinyin>.*?)</td>
</td>
    <td width="50%">&nbsp;<span class="lable">注音二式</span>(?P<bopomofo2>.*?)</td>
  </tr>
(?:  <tr>
    <td>&nbsp;<span class="lable">相似詞</span>　(?P<synonyms>[\s\S]*?)</td>
    <td>&nbsp;<span class="lable">相反詞</span>　(?P<antonyms>[\s\S]*?)</td>
  </tr>
)?  <tr>
    <td colspan="2">
      <table border="0" valign="top">
(?P<detail>[\s\S]*?)</table>
    </td>
  </tr>
</table>
''', html)
    assert m, 'firsr level parse fail'
    d = dict(m.groupdict())

    for k, v in d.items():
        if v:
            d[k] = normalize(k, v)

    heteronym = dict(
            bopomofo=d['bopomofo'],
            bopomofo2=d['bopomofo2'],
            pinyin=d['pinyin'],
            )
    basic = parse_basic(d['titledata'])
    if 'stroke_count' in basic:
        basic['stroke_count'] = int(basic['stroke_count'])
    if 'non_radical_stroke_count' in basic:
        basic['non_radical_stroke_count'] = int(basic['non_radical_stroke_count'])
    heteronym['definitions'] = parse_defs(d['detail'], d)

    associate_to_defs('synonyms', d, heteronym['definitions'])
    associate_to_defs('antonyms', d, heteronym['definitions'])

    for k, v in heteronym.items():
        if not v:
            del heteronym[k]

    return basic, heteronym

def normalize(key, s):
    # remove highlight
    s = re.sub(r'<span class="key">(.+?)</span>', r'\1', s)

    def mapping(m):
        c = m.group(1)
        if c in number_map:
            return number_map[c]
        if c in pos_map:
            return pos_map[c]
        if c in phonetone_map:
            return phonetone_map[c]
        return '{[%s]}' % c
    s = re.sub(r'\{\[([0-9a-f]{4})\]\}', mapping, s)
    s = re.sub(r'<img src="images/([0-9a-f]{4}).jpg" border="0"\s*/>(?:&nbsp;)?', mapping, s)

    # Fix ⼁(U+2F01)
    s = s.replace(u'如、－｜', u'如、－⼁')
    s = s.replace(u'｜，下上通也', u'⼁，下上通也')
    if key == 'titledata':
        s = s.replace(u'｜', u'⼁')

    s = s.translate(normal_map)
    s = re.sub(ur'˙(?![\u3100-\u312f])', u'．', s)

    # workaround bad parentheses
    s = re.sub(ur'（([^()（）]+)\)', r'(\1)', s)
    s = re.sub(ur'\(([^()（）]+)）', r'(\1)', s)
    s = re.sub(ur'（(\d{1,2})）', r'(\1)', s)

    s = s.strip()
    return s

def verify_parsed_result(d):
    for k, v in d.items():
        if v and '</' in unicode(v):
            logging.warn('output contains html tag')
            break

def json_dumps(o):
    s = json.dumps(o, sort_keys=True, ensure_ascii=False, indent=1)

    s = re.sub(r'\n( +)',
            lambda m: '\n'+'\t'*len(m.group(1)),
            s)
    s = s.replace(' \n', '\n')
    return s

def fix_big5_data(s):
    # ---------------------------------------------------------------
    # special case
    # html/A5AC/150.html 布爾諾(Br??no)
    # Should be Brno, or Brunn
    s = s.replace('(Br\x97\xe7no)', '(Brno)')
    # html/C3F8/34.html
    s = s.replace('\xa3\xf6', '</tr><tr><td valign=top>')

    # ---------------------------------------------------------------
    # html/AA69/63.html 波哥大(Ｂｏｇｏｔ??)
    s = s.replace('\xfe\x69', '{[fe69]}')
    # html/AA69/122.html 波爾(Heinrich B??ll)
    s = s.replace('\x92\x70', '{[9270]}')
    # html/AB6B/2.html 勃姆(B??hm Theobald)
    s = s.replace('\x92\x70', '{[9270]}')
    # html/AC66/24.html 柏卡里(Muhammad ibn Ismail al-Bukh??r??)
    s = s.replace('\xfe\x68', '{[fe68]}')
    s = s.replace('\xfe\x70', '{[fe70]}')
    # html/AC66/30.html 柏濟力阿斯(J??ns Jacob Berzelius)
    s = s.replace('\x92\x70', '{[9270]}')
    # html/ACA5/5.html 洛梅(Ｌｏｍ??)
    s = s.replace('\xfe\x6d', '{[fe6d]}')
    # html/AD7B/9.html 迦旃延(ｋａｔｙ??ｙａｎａ)
    s = s.replace('\xfe\x68', '{[fe68]}')
    # html/AE4C/7.html 夏目漱石(Natsume s??seki)
    s = s.replace('\xfe\x74', '{[fe74]}')
    # html/B14B/56.html 密支那(Myitkyin??)
    s = s.replace('\xfe\x68', '{[fe68]}')
    # html/B3CD/1.html 凱末爾(Atat??rk，Kemal)
    s = s.replace('\x97\xe7', '{[97e7]}')
    # html/B648/50.html 象牙海岸(C??te  d'Ivoire)
    s = s.replace('\x9a\xeb', '{[9aeb]}')
    # html/B648/51.html 象牙海岸共和國(Ｒｅｐｕｂｌｉｃ　ｏｆ　Ｃ??ｔｅ　ｄ'Ｉｖｏｉｒｅ)
    s = s.replace('\x9a\xeb', '{[9aeb]}')
    # html/C4AC/19.html 蘇黎士(Z??rich)
    s = s.replace('\x97\xe7', '{[97e7]}')
    return s


def decode_big5(s):
    try:
        return s.decode('big5')
    except UnicodeDecodeError:
        pass

    try:
        s = fix_big5_data(s)
        return s.decode('big5')
    except UnicodeDecodeError:
        logging.exception('bad big5 char?')
        return None

def process_data(data):
    try:
        content = decode_big5(data)
        if not content:
            return False

        basic, heteronym = parse_heteronym(content)

        title = basic['title']
        logging.debug('title = '+title)

        if title in basic_data:
            # TODO check consistent?
            pass
        basic_data[title] = basic
        heteronym_data[title].append(heteronym)

        logging.debug(json_dumps(basic))
        logging.debug(json_dumps(heteronym))

    except AssertionError:
        logging.exception('parse fail')
        return False
    return True

def dump_json():
    logging.info('dump_json')
    with codecs.open('dict-revised.json', 'w', 'utf8') as f:
        for k in basic_data.keys():
            basic_data[k]['heteronyms'] = heteronym_data[k]
        jn = json_dumps(sorted(basic_data.values(),
            key=lambda x: x['title']))
        f.write(jn + '\n')

def post_processing():
    logging.info('dedup heteronyms')
    for title, hs in heteronym_data.items():
        hs_new = []
        known = set()
        for h in hs:
            jn = json.dumps(h)
            if jn in known:
                continue
            known.add(jn)
            hs_new.append(h)
        heteronym_data[title] = hs_new

    logging.info('remove phonetic index')
    for title, hs in heteronym_data.items():
        assert hs

        # order by <1>,<2>,...
        hs.sort(key=lambda h: h.get('bopomofo'))

        known_bpmf = set()
        for h in hs:
            # remove <1>
            if not h.get('bopomofo'):
                continue
            for k in ('bopomofo', 'bopomofo2', 'pinyin'):
                if re.match(r'^<\d+>', h[k]):
                    h[k] = re.sub('^<\d+>', '', h[k])
            known_bpmf.add(h['bopomofo'])

        # remove <1> from definition
        for h in hs:
            defs = h['definitions']
            defs_new = []
            for d in defs:
                m = re.match(ur'^<(\d+)>(.+)', d['def'])
                if m and re.search(re_bpmf, m.group(2)):
                    # TODO verify consistency
                    continue
                defs_new.append(d)
            if len(defs) != len(defs_new):
                h['definitions'] = defs_new


def rawdata_iter():
    for root, dirs, files in os.walk('crawl/html'):
        #if count_parsed >= 1000:
        #    break
        logging.info(root)
        dirs.sort()
        for fn in sorted(files):
            if not fn.endswith('.html'):
                continue
            path = os.path.join(root, fn)
            logging.debug(path)
            yield file(path).read()

def rawdata_iter():
    import tarfile
    tf = tarfile.TarFile.open('crawl/dict-revised.rawhtml.201301.tar.bz2')
    lastdir = ''
    for ti in tf:
        d, _ = os.path.split(ti.name)
        if d != lastdir:
            logging.info(d)
        lastdir = d

        if not ti.name.endswith('.html'):
            continue
        logging.debug(ti.name)
        yield tf.extractfile(ti).read()


def main():
    setup_logging()
    build_normal_map()

    count_parsed = 0
    count_file = 0
    try:
        for rawdata in rawdata_iter():
            count_file += 1
            if process_data(rawdata):
                count_parsed += 1
            logging.debug('parsed %d/%d' % (count_parsed, count_file))

        post_processing()
        dump_json()
    finally:
        logging.info('%d files, parsed %d' % (count_file, count_parsed))

if __name__ == '__main__':
    main()
