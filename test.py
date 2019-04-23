import re
import requests
from bs4 import BeautifulSoup
import datetime
from janome.tokenizer import Tokenizer
import random

# tokennizer作成
t = Tokenizer()

# 指定した品詞の文字列を取得するメソッド
def getSurfaceOf(token_list, part_of_speech):
  return [token.surface for token in token_list if token.part_of_speech.startswith(part_of_speech)]

# 第一引数の文字列の【名詞,一般】トークンを、第二引数の入れ替え候補リストの中からランダムに選ばれた単語と入れ替える
def swapNoun(target, candidate_list_to_replace):
  # 分かち書き
  wakati = [token.surface for token in t.tokenize(target)]
  # 分かち書きに対応した品詞リスト
  part_of_speech_list = [
      token.part_of_speech for token in t.tokenize(target)]
  # 名詞,一般のインデックスを取得
  target_index_list = [i for i, x in enumerate(
      part_of_speech_list) if x.startswith('名詞,一般')]
  # 名詞,一般を、事前に取得した名詞,一般リストの中からランダムに選んだものと入れ替える
  for i in target_index_list:
    wakati[i] = len(candidate_list_to_replace) and random.choice(
        candidate_list_to_replace) or print('[candidate_list_to_replace()] is nothing.')
  # 入れ替えた結果を返却する
  return "".join(wakati)

# Googleで検索する（キーワードとstart位置を指定してGoogle検索結果のURLのタグのリストを返却する関数）
def get_url_tag_list(keyword, start):
  url = 'https://www.google.co.jp/search'
  headers = {
      "User-Agent": "Mozilla/5.0 (Linux; U; Android 4.1.2; ja-jp; SC-06D Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"}
  # URLパラメータ作成：tbm: 検索パターンの指定, start: 検索をスタートする開始位置
  #（'+'がエンコードされる件の参照：https://www.monotalk.xyz/blog/nonencoded-querystring-on-python-requests/）
  search_params = {'q': keyword, 'start': start}
  p_str = "&".join("%s=%s" % (k, v) for k, v in search_params.items())
  # HTTP通信と結果の取得・パース
  search_res = requests.get(url, params=p_str, headers=headers)
  search_soup = BeautifulSoup(search_res.text, 'html.parser')
  # 検索結果一覧
  url_tag_list = search_soup.select('.C8nzq.BmP5tf:not(.d5oMvf)')
  return url_tag_list

# Yahoo!で検索する
def search_by_yahoo(keyword, start):
  url = 'https://search.yahoo.co.jp/search'
  headers = {
      "User-Agent": "Mozilla/5.0 (Linux; U; Android 4.1.2; ja-jp; SC-06D Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"}
  search_params = {"ei": "UTF-8", "fr": "top_smf",
                   "meta": "vc=", "p": keyword, "b": start or 1}
  p_str = "&".join("%s=%s" % (k, v) for k, v in search_params.items())
  search_res = requests.get(url, params=p_str, headers=headers)
  search_soup = BeautifulSoup(search_res.text, 'html.parser')
  base_list = search_soup.select(".sw-CardBase")
  url_tag_list = []
  for b in base_list:
    if b.get("data-pos"):
      url_tag_list.append(b.a)
  return url_tag_list

# bingで検索する https://www.bing.com/search?q=python&form=QBLH
def search_by_bing(keyword, start):
  url = "https://www.bing.com/search"
  headers = {
      "User-Agent": "Mozilla/5.0 (Linux; U; Android 4.1.2; ja-jp; SC-06D Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"}
  search_params = {"q": keyword, "form": "QBLH", "first": start}
  p_str = "&".join("%s=%s" % (k, v) for k, v in search_params.items())
  search_res = requests.get(url, params=p_str, headers=headers)
  search_soup = BeautifulSoup(search_res.text, 'html.parser')
  # <li class="b_algo"> 直下のaタグが検索結果
  base_list = search_soup.select(".b_algo")
  url_tag_list = []
  for b in base_list:
    url_tag_list.append(b.a)
  return url_tag_list

# URLのタグのリストから指定したドメインのタグを削除する（削除対象のドメインはリストで指定する）
def exclude_specific_domains(url_tag_list, target_list):
  print([u['href'] for u in url_tag_list])
  print(f'{", ".join(target_list)}を除外します')
  escaped_target_list = map(re.escape, target_list)
  target = f'({"|".join(escaped_target_list)})'
  result_list = [url_tag for url_tag in url_tag_list if not re.match(
      f'{target}.*?', url_tag['href'])]
  exclusion_num = len(url_tag_list) - len(result_list)
  if exclusion_num > 0:
    print(f'{exclusion_num}件除外しました')
  else:
    print('除外対象なし')
  return result_list

# 指定した値までGoogle検索でURLタグをリストアップする(第3引数のドメインを除外した上で)
def get_url_tag_list_up_to_specified_number(keyword, number, exclusion_target_list):
  result_list = []
  loop_index = 0
  while len(result_list) < number:
    url_tag_list = get_url_tag_list(keyword, loop_index * 10)
    url_tag_list_excluding_target_domain = exclusion_target_list and exclude_specific_domains(
        url_tag_list, exclusion_target_list) or url_tag_list
    result_list.extend(url_tag_list_excluding_target_domain)
    loop_index += 1

  return result_list[: number]

# 指定した数までYahoo!で検索する(第3引数のドメインを除外した上で)
def search_by_yahoo_up_to_specified_number(keyword, number, exclusion_target_list):
  result_list = []
  while len(result_list) < number:
    url_tag_list = search_by_yahoo(keyword, len(result_list) + 1)
    url_tag_list_excluding_target_domain = exclusion_target_list and exclude_specific_domains(
        url_tag_list, exclusion_target_list) or url_tag_list
    result_list.extend(url_tag_list_excluding_target_domain)

  return result_list[: number]

# 指定した数までbingで検索する(第3引数のドメインを除外した上で)
def search_by_bing_up_to_specified_number(keyword, number, exclusion_target_list):
  result_list = []
  while len(result_list) < number:
    url_tag_list = search_by_bing(keyword, len(result_list) + 1)
    url_tag_list_excluding_target_domain = exclusion_target_list and exclude_specific_domains(
        url_tag_list, exclusion_target_list) or url_tag_list
    result_list.extend(url_tag_list_excluding_target_domain)

  return result_list[: number]


tag_list = search_by_bing_up_to_specified_number("python", 20, [])
for tag in tag_list:
  print(tag['href'])





#______________________________________
#
# マルコフ連鎖のテスト
# ---------------------


import markovify

# Get raw text as string.
with open("markovify_test.txt") as f:
    text = f.read()

# Build the model.
text_model = markovify.Text(text)

# Print five randomly-generated sentences
for i in range(5):
    print(text_model.make_sentence())

# Print three randomly-generated sentences of no more than 140 characters
for i in range(3):
    print(text_model.make_short_sentence(140))