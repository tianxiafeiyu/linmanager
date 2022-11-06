# -- coding: utf-8 --
import os
import re
import uuid
from urllib.parse import urlparse

import requests

from fake_useragent import UserAgent
from Crypto.Cipher import AES

import multiprocessing
import shutil

CRYPTO_ENABLE = True
OUTPUT_DIR = None
TIMEOUT = 10


class M3U8(object):

    def __init__(self, url):

        self.encrypt_method = None
        self.key_uri = None
        self.encrypt_iv = None
        self.ts_urls = []

        parse_result = urlparse(url)
        self.base_url = '://'.join([parse_result.scheme, parse_result.netloc])

        self.m3u8_lines = self._parse_m3u8_url(url)

        if self.m3u8_lines:
            self._parse_ts_url(self.base_url, self.m3u8_lines)
        else:
            print('Parse m3u8 url error!')

    def _parse_m3u8_url(self, url):
        # 解析M3U8 url，判断是否存在跳转
        m3u8_contents = None
        while m3u8_contents is None:
            resp = get_response(url)
            m3u8_contents = resp.text

        if 'EXT-X-STREAM-INF' in m3u8_contents:
            # 存在跳转，需重新组合真实路径
            m3u8_lines = m3u8_contents.split('\n')
            actual_url = None
            for index, line_content in enumerate(m3u8_lines):
                if '.m3u8' in line_content:
                    actual_url = line_content
                    break

            url = ''.join([self.base_url, actual_url])
            print('Use embeded URL:%s' % url)

        m3u8_content = get_response(url).text
        m3u8_lines = m3u8_content.split('\n')

        return m3u8_lines
        
    def _parse_ts_url(self, base_url, m3u8_lines):
        for index, line_content in enumerate(m3u8_lines):
            if 'EXT-X-KEY' in line_content:
                # 解析密钥
                content_units = line_content.split(',')
                for content_unit in content_units:
                    if 'METHOD' in content_unit:
                        if self.encrypt_method is None:
                            self.encrypt_method = content_unit.split('=')[-1]

                    elif 'URI' in content_unit:
                        if 'ccb.com' in content_unit:
                            self.key_uri = content_unit.split('"')[1]
                        else:
                            key_path = content_unit.split('"')[1]

                            self.key_uri = base_url + '/' + key_path  # 拼出key解密密钥URL
                    elif 'IV' in content_unit:
                        if self.encrypt_iv is None:
                            self.encrypt_iv = content_unit.split('=')[-1]
            if 'EXTINF' in line_content:
                # 拼出ts片段的URL
                if m3u8_lines[index + 1].startswith('/'):
                    ts_url = base_url + m3u8_lines[index + 1]
                else:
                    ts_url = base_url + '/' + m3u8_lines[index + 1]
                self.ts_urls.append(ts_url)


def get_response(url):
    return requests.get(url, headers=CHROME_HEADERS, timeout=10, proxies=PROXIES)


def download_ts_files(ts_list, tmp_dir, process_id):
    cookies = None
    session = requests.Session()
    for i, ts_url in enumerate(ts_list):
        print('%d, download %s, index:%d/%d, %s' % (process_id, os.path.basename(tmp_dir), i, len(ts_list), ts_url))
        retry_times = 100
        tmp_file = os.path.join(tmp_dir, ts_url.rsplit('/', 1)[-1])
        if os.path.exists(tmp_file):
            continue

        while retry_times > 0:
            ret_sucess, cookies = download_ts(ts_url, tmp_file, session, cookies)
            retry_times -= 1
            if ret_sucess:
                break


def download_ts(ts_url, tmp_file, session, cookies=None):
    try:
        resp = session.get(
            ts_url,
            headers=CHROME_HEADERS,
            timeout=TIMEOUT,
            cookies=cookies,
            proxies=PROXIES
        )
        if cookies is None:
            cookies = session.cookies

        with open(tmp_file, 'wb') as f:
            f.write(resp.content)
        return True, cookies
    except Exception as e:
        Warning('Error:%s' % str(e))
        return False, cookies


def decrypt_files(ts_urls, tmp_dir, encrypt_method, key_str):
    key_bytes = bytes(key_str, 'utf-8')
    if 'AES' in encrypt_method:
        cryptor = AES.new(key_bytes, AES.MODE_CBC, None)
    else:
        raise NotImplementedError('%s has not implented yet!' % encrypt_method)

    for i, ts_url in enumerate(ts_urls):
        tmp_file = os.path.join(tmp_dir, ts_url.rsplit('/', 1)[-1])
        decrypt_file = os.path.join(tmp_dir, 'decrypt_' + ts_url.rsplit('/', 1)[-1])
        if not os.path.exists(tmp_file):
            raise FileNotFoundError('Some files fail to download, try again!')
        with open(tmp_file, 'rb') as f_encrypt:
            encrypt_content = f_encrypt.read()

        with open(decrypt_file, 'wb') as f:
            f.write(cryptor.decrypt(encrypt_content))


def download_m3u8_video(url, out_dir, out_name, process_num):
    out_path = os.path.join(out_dir, out_name)
    tmp_dir = os.path.join(out_dir, os.path.splitext(os.path.basename(out_name))[0])
    if os.path.exists(out_path) and not os.path.exists(tmp_dir):
        # 该任务已完成下载
        print('Input name is existed:%s!' % out_name)
        return

    m3u8_inst = M3U8(url)
    ts_len = len(m3u8_inst.ts_urls)
    print('ts length:%d' % ts_len)

    if ts_len > 0:
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)

        process_list = []
        per_process_num = int(ts_len / process_num)

        # 启用多进程下载视频
        for i in range(process_num):
            id_start = i * per_process_num
            id_end = (i + 1) * per_process_num
            if i == process_num - 1:
                id_end = ts_len
            cur_process = multiprocessing.Process(
                target=download_ts_files, args=(m3u8_inst.ts_urls[id_start:id_end], tmp_dir, i))
            cur_process.start()
            # search_ip(ip_prefix, database, table_name, ip_start, ip_end, i)
            process_list.append(cur_process)

        for process_item in process_list:
            process_item.join()

        # 若有加密，尝试解密文件
        if CRYPTO_ENABLE and m3u8_inst.encrypt_method not in ['NONE', None, 'None']:
            print('encrypt method:%s' % m3u8_inst.encrypt_method)
            print('key uri:%s' % m3u8_inst.key_uri)
            key_str = get_response(m3u8_inst.key_uri)
            decrypt_files(m3u8_inst.ts_urls, tmp_dir, m3u8_inst.encrypt_method, key_str)

        print('Merging to one file:%s' % out_path)
        with open(out_path, 'wb') as f_out:
            for i, ts_url in enumerate(m3u8_inst.ts_urls):
                tmp_file = os.path.join(tmp_dir, ts_url.rsplit('/', 1)[-1])
                decrypt_file = os.path.join(tmp_dir, 'decrypt_' + ts_url.rsplit('/', 1)[-1])
                dst_file = decrypt_file if CRYPTO_ENABLE and m3u8_inst.encrypt_method not in ['NONE', None,
                                                                                              'None'] else tmp_file

                if not os.path.exists(dst_file):
                    print('Some files fail to download or decrypt, try again!')
                    return

                with open(dst_file, 'rb') as f:
                    f_out.write(f.read())

        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


ua = UserAgent()

M3U8_URL_REGEX = r'https:\\*/\\*/[\\\w\-_\.]+[\\\w\-\.,@?^=%&:/~\+#]*\.m3u8'
CHROME_HEADERS = {'User-Agent': ua.random}
PROXIES = {"http": "127.0.0.1:7890", "https": "127.0.0.1:7890"}


# python catch_m3u8.py url 保存名称 起始序号
def download(url, out_dir):
    r = get_response(url)
    html = r.text

    matches = re.findall(M3U8_URL_REGEX, html)
    if not matches:
        print("获取m3db地址失败。")
        return False

    m3u8_url = matches[0]
    m3u8_url = eval(repr(m3u8_url).replace('\\', ''))
    print("开始下载：%s" % m3u8_url)

    # 获取cpu核数
    process_num = int(multiprocessing.cpu_count() / 2)
    print("启用线程数：%s" % process_num)

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if os.path.isfile(m3u8_url):
        # 连续下载多个路径的视频
        with open(m3u8_url, 'r') as f_url:
            url_list = f_url.readlines()
        for url_idx, url_line in enumerate(url_list):
            save_name = uuid.uuid4().hex + '.mp4'
            download_m3u8_video(url_line.strip(), out_dir, save_name, process_num)
    else:
        save_name = uuid.uuid4().hex + '.mp4'
        download_m3u8_video(m3u8_url, out_dir, save_name, process_num)

    return True
