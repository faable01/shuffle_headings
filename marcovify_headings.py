import re
import requests
from bs4 import BeautifulSoup
import datetime
from janome.tokenizer import Tokenizer
import random
import markovify
from concurrent.futures import ThreadPoolExecutor
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# InsecureRequestWarningを非表示にする
urllib3.disable_warnings(InsecureRequestWarning)

# tokennizer作成
t = Tokenizer()

# ユーザ入力 >>> シャッフル元ページの取得件数
number_of_pages = int(input('シャッフル元となるページの取得件数を入力してください >>> '))

# ユーザ入力 >>> 除外するドメインのリスト
user_input = input('除外するドメインを指定してください（スペースを空けて複数指定可能） >>> ').strip() or None
exclusion_domain_list = user_input and user_input.split() or []

# 検索エンジンの指定
search_engine = 0
while not search_engine in (1, 2, 3):
  search_engine = int(input('検索エンジンを選択してください。 1. Google, 2. Yahoo!, 3. Bing（1, 2, 3のどれかを押してください） >>> '))

# ユーザ入力 >>> 検索キーワード
search_keyword = '+'.join(input('検索キーワードを入力してください >>> ').split())

# デフォルトの削除ドメイン
default_exclusion_domain_list = ["https://www.amazon.co.jp/", "https://www.rakuten.co.jp/", "https://kakaku.com/", "https://twitter.com/", "https://www.instagram.com/", "https://www.cosme.net/", "https://beauty.hotpepper.jp/", "https://search.rakuten.co.jp/"]
exclusion_domain_list.extend(default_exclusion_domain_list)

# 必須KW
must_keyword = input('必須キーワードを入力してください >>> ')


# ______________________________________________________________________________________________
#
# ファイル操作系
# -----------------
def write_next_line(filename, str):
  with open(filename, mode="a") as f:
    f.write("\n")
    f.write(str)

def write(filename, str):
  with open(filename, mode="w", encoding="UTF-8") as f:
    f.write(str)

def read(filename):
  with open(filename) as f:
    return f.read()

def read_lines_as_list(filename):
  with open(filename) as f:
    return f.readlines()

# ______________________________________________________________________________________________
#
# 文字列操作系
# -----------------

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

# 文字列に特定のキーワードが入っているかを確認する関数
def has_kw(target_kw, target_str):
  return target_kw in target_str

# 文字列の配列の要素を改行で結合する
def create_str_lines(str_list):
  return "\n".join(str_list)

# 対象の文字列を分ち書きする
def create_wakati_list(target: str) -> list:
  return t.tokenize(target, wakati=True)

# 分ち書きしたリストを半角スペースで繋げた文字列を返す
def create_wakati_line(wakati_list: list) -> str:
  return " ".join(wakati_list)

# 文字列を分ち書きして半角スペースで区切った文字列を返す
def write_wakati(target: str) -> str:
  return create_wakati_line(create_wakati_list(target))

# エスケープを削除する（二重バックスラッシュを一重にする）
def delete_escape(target: str) -> str:
  return target.replace("¥¥", "¥")

# ______________________________________________________________________________________________
#
# 検索系
# -----------------

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
  search_res = requests.get(url, params=p_str, headers=headers, verify=False)
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
  search_res = requests.get(url, params=p_str, headers=headers, verify=False)
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
  search_res = requests.get(url, params=p_str, headers=headers, verify=False)
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

    # url_tag_listが一件も存在しない場合にはループを抜ける
    if len(url_tag_list) is 0:
      break
    
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

    # url_tag_listが一件も存在しない場合にはループを抜ける
    if len(url_tag_list) is 0:
      break
    
    url_tag_list_excluding_target_domain = exclusion_target_list and exclude_specific_domains(
        url_tag_list, exclusion_target_list) or url_tag_list
    result_list.extend(url_tag_list_excluding_target_domain)
  return result_list[: number]
  
# 指定した数までbingで検索する(第3引数のドメインを除外した上で)
def search_by_bing_up_to_specified_number(keyword, number, exclusion_target_list):
  result_list = []
  while len(result_list) < number:
    url_tag_list = search_by_bing(keyword, len(result_list) + 1)

    # url_tag_listが一件も存在しない場合にはループを抜ける
    if len(url_tag_list) is 0:
      break
    
    url_tag_list_excluding_target_domain = exclusion_target_list and exclude_specific_domains(
        url_tag_list, exclusion_target_list) or url_tag_list
    result_list.extend(url_tag_list_excluding_target_domain)
  return result_list[: number]

# 通信結果を判定する
def is_res_ng(res):
  try:
    res.raise_for_status()
    # 例外なし => OK出力
    print("通信結果判定：正常")
    return False
  
  except requests.RequestException as e:
    # 例外あり => NG出力
    print("通信結果判定：異常（ページ存在なし等）")
    print(e)
    return True


# ______________________________________________________________________________________________
#
# メイン処理系
# -----------------

# URLのタグから見出しを取得する
def get_headings(url_tag):
  
  headings = {'h2': [], 'h3': [], 'h4': []}
  
  # 取得したURLにアクセス
  h = {
      "User-Agent": "Mozilla/5.0 (Linux; U; Android 4.1.2; ja-jp; SC-06D Build/JZO54K) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"}
    
  # 通信実行（例外時はtracebackを出力して関数を終了する）
  try:
    # urlListのURLをhttpに直す
    target_url = url_tag['href'].replace("https", "http")
    res = requests.get(target_url, headers=h, verify=False)
  except:
    print("通信時例外発生_例外詳細：")
    # traceback詳細出力
    import traceback
    traceback.print_exc()
    return False
  
  # 通信結果が異常
  if is_res_ng(res):
    return False
  
  # WEBページの文字コードを推測
  res.encoding = res.apparent_encoding
  if res.encoding != 'UTF-8' and res.encoding != 'utf-8':
    print(f'UTF-8以外の文字コードを検出：{res.encoding}')
    if res.encoding == 'Windows-1254':
      print('誤りだと思われる文字コード(Windows-1254)を検出しました。UTF-8に変換します。')
      res.encoding = 'UTF-8'

  soup = BeautifulSoup(res.text, 'html.parser')

  # 見出し取得
  h_list = soup.select('h2, h3, h4')

  for h in h_list:
    h_text = h.text.strip()

    if h.name == 'h2' and has_kw(must_keyword, h_text):
      headings['h2'].append(h_text and h_text.replace("・", "") or "")

    elif h.name == 'h3' and has_kw(must_keyword, h_text):
      headings['h3'].append(h_text and h_text.replace("・", "") or "")

    elif h.name == 'h4' and has_kw(must_keyword, h_text):
      headings['h4'].append(h_text and h_text.replace("・", "") or "")
  
  return headings

# 見出しリストから名詞・一般リストを作成する
def get_noun_list(headings):

  h2_noun = []
  h3_noun = []
  h4_noun = []
  for h in headings['h2']:
    h2_noun.extend(getSurfaceOf(t.tokenize(h), '名詞,一般'))
  for h in headings['h3']:
    h3_noun.extend(getSurfaceOf(t.tokenize(h), '名詞,一般'))
  for h in headings['h4']:
    h4_noun.extend(getSurfaceOf(t.tokenize(h), '名詞,一般'))
  
  noun_list = {
      'h2': h2_noun, 
      'h3': h3_noun, 
      'h4': h4_noun
    }
  print(f"noun_list${noun_list}")
  return noun_list

# 引数で指定したURLタグのリストに従い、見出し取得を行う
def get_all_headings(urlList: list) -> list:
  # 全見出し + 名詞,一般　格納変数
  all = {'h2': [], 'h3': [], 'h4': []}
  
  print(f'キーワードに基づきページを取得します（全{len(urlList)}ページ）')
  for i, u in enumerate(urlList):

    print(f'{i + 1}件目取得中...')
    headings = get_headings(u)

    # 通信失敗時
    if not headings:
      print("次ページに処理を移行します")
      continue
    
    all['h2'].extend([write_wakati(h) for h in headings['h2']])
    all['h3'].extend([write_wakati(h) for h in headings['h3']])
    all['h4'].extend([write_wakati(h) for h in headings['h4']])
    print('完了')

  print('全URLの見出しの取得を完了しました。')
  return all

# 引数で指定したURLタグのリストに従い、複数スレッドでアクセス・見出し取得を行う
def multi_get_all_headings(urlList):

  # 全見出し + 名詞,一般　格納変数
  all = {'h2': [], 'h3': [], 'h4': []}

  # 複数スレッドでの関数実行
  with ThreadPoolExecutor() as pool:
    for i, headings in enumerate(pool.map(get_headings, urlList)):
      print(f'{i + 1}件目解析中...')
      
      # 通信失敗時
      if not headings:
        print("次ページに処理を移行します")
        continue
      
      all['h2'].extend([write_wakati(h) for h in headings['h2']])
      all['h3'].extend([write_wakati(h) for h in headings['h3']])
      all['h4'].extend([write_wakati(h) for h in headings['h4']])
      print('完了')

  print('全URLの見出しの取得を完了しました。')
  return all
  
# 第一引数の見出しリストをシャッフルする関数 (第一引数：{'h2', 'h3', 'h4'})
def shuffle_headings(all):
  
  # シャッフル候補の名詞・一般リストを全件見出しリストから取得
  noun_list = get_noun_list(all)

  # 各h2に対してh3を2~3個、h3に対して3回に1回の割合くらいでh4を2~3個
  num_h2 = random.randrange(3, 6, 1)
  for i in range(num_h2):

    # 骨組みとして、ベースとなる見出しを取得する
    base_h2 = len(all['h2']) and random.choice(
        all['h2']) or print("取得したh2見出しがありません")

    # ベースの名詞,一般トークンを入れ替え候補リストの中からランダムに選ばれた単語と入れ替える
    result_h2 = base_h2 and swapNoun(base_h2, noun_list['h2']) or False
    result_h2 and print(result_h2)
    num_h3 = random.randrange(2, 4, 1)

    for j in range(num_h3):
      base_h3 = len(all['h3']) and random.choice(
          all['h3']) or print("取得したh3見出しがありません")
      result_h3 = base_h3 and swapNoun(base_h3, noun_list['h3']) or False
      result_h3 and print(f'・{result_h3}')
      num_h4 = random.choice([0, 0, 0, 0, 2, 3])

      for k in range(num_h4):
        base_h4 = len(all['h4']) and random.choice(
            all['h4']) or print("取得したh4見出しがありません")
        result_h4 = base_h4 and swapNoun(base_h4, noun_list['h4']) or False
        result_h4 and print(f'・・{result_h4}')
    
    print('')

# 見出しシャッフルツール実行メソッド
def shuffle_headings_app():
  
  # 全見出し + 名詞,一般　格納変数
  all = {'h2': [], 'h3': [], 'h4': []}

  # 全件URLリスト
  urlList = None
  if search_engine == 1:
    urlList = get_url_tag_list_up_to_specified_number(search_keyword, number_of_pages, exclusion_domain_list)
  elif search_engine == 2:
    urlList = search_by_yahoo_up_to_specified_number(search_keyword, number_of_pages, exclusion_domain_list)
  elif search_engine == 3:
    urlList = search_by_bing_up_to_specified_number(search_keyword, number_of_pages, exclusion_domain_list)
  
  print(f'キーワードに基づき、シャッフル元となるページを取得します（全{number_of_pages}ページ）')
  for i, u in enumerate(urlList):

    print(f'{i + 1}件目取得中...')
    headings = get_headings(u)
    
    # 通信失敗時
    if not headings:
      print("次ページに処理を移行します")
      continue
    
    all['h2'].extend(headings['h2'])
    all['h3'].extend(headings['h3'])
    all['h4'].extend(headings['h4'])
    print('完了')

  print('全URLの見出しの取得を完了しました。')
  print('見出しをシャッフル・再構築します。')

  # 見出し構成をランダムに作成する\
  loop_count = 1
  while True:
    print('\n____________________________________________\n')
    print(f'構成案 {loop_count}件目\n---------------------------\n')

    # 第一引数の見出しリストをシャッフルしてprintする
    shuffle_headings(all)

    is_retry = ""
    while is_retry != 'YES' and is_retry != 'NO':
      is_retry = input('もう一度シャッフル・再構築しますか？ ( YES / NO ) >>> ')

      if is_retry == 'YES' or is_retry == 'yes' or is_retry == 'y' or is_retry == 'Y':
        is_retry = 'YES'
      elif is_retry == 'NO' or is_retry == 'no' or is_retry == 'n' or is_retry == 'N':
        is_retry = 'NO'

    if is_retry == 'YES':
      loop_count += 1
    elif is_retry == 'NO':
      break

def marcovify_headings(all):
  # 二次元リストをスペース + 改行区切りで文字列に変換
  all_h2_str = create_str_lines(all['h2'])
  all_h3_str = create_str_lines(all['h3'])
  all_h4_str = create_str_lines(all['h4'])
  all_line = f"{all_h2_str}\n{all_h3_str}\n{all_h4_str}"

  # log
  # write("all_h2.log", all_h2_str)
  # write("all_h3.log", all_h3_str)
  # write("all_h4.log", all_h4_str)
  write("all_line.log", all_line)

  # Build the model.
  # model_h2 = markovify.NewlineText(all_h2_str)
  # model_h3 = markovify.NewlineText(all_h3_str)
  # model_h4 = markovify.NewlineText(all_h4_str)
  text_model = markovify.NewlineText(all_line)

  # ---- 見出し構築・出力 ----

  # h2を3〜5個
  num_h2 = random.randrange(3, 6, 1)
  for i in range(num_h2):

    # h2 = print(model_h2.make_sentence())
    # print(h2)
    sentence_h2 = text_model.make_sentence()
    sentence_h2 and print(sentence_h2.replace(" ", ""))

    # 各h2に対してh3を2~3個
    num_h3 = random.randrange(2, 4, 1)
    for j in range(num_h3):

      # h3 = print(model_h3.make_sentence())
      # print(f'・{h3}')
      sentence_h3 = text_model.make_sentence()
      sentence_h3 and print(f'・{sentence_h3.replace(" ", "")}')
      
      # h3に対して3回に1回の割合くらいでh4を2~3個
      num_h4 = random.choice([0, 0, 0, 0, 2, 3])
      for k in range(num_h4):

        # h4 = print(model_h4.make_sentence())
        # print(f'・・{h4}')
        sentence_h4 = text_model.make_sentence()
        sentence_h4 and print(f'・・{sentence_h4.replace(" ", "")}')
    
    print('')


def marcovify_headings_app():

  # 全件URLリスト
  urlList = None
  if search_engine == 1:
    urlList = get_url_tag_list_up_to_specified_number(search_keyword, number_of_pages, exclusion_domain_list)
  elif search_engine == 2:
    urlList = search_by_yahoo_up_to_specified_number(search_keyword, number_of_pages, exclusion_domain_list)
  elif search_engine == 3:
    urlList = search_by_bing_up_to_specified_number(search_keyword, number_of_pages, exclusion_domain_list)

  # URLリストの要素が存在しない場合、処理を終了する
  if len(urlList) is 0:
    return
  
  # 全見出し　{'h2': [...], 'h3': [...], 'h4': [...]}
  all = multi_get_all_headings(urlList)

  loop_count = 1
  while True:
    print('\n____________________________________________\n')
    print(f'構成案 {loop_count}件目\n---------------------------\n')

    # マルコフ連鎖で見出しを自動生成する
    marcovify_headings(all)

    is_retry = ""
    while is_retry != 'YES' and is_retry != 'NO':
      is_retry = input('もう一度シャッフル・再構築しますか？ ( YES / NO ) >>> ')

      if is_retry == 'YES' or is_retry == 'yes' or is_retry == 'y' or is_retry == 'Y':
        is_retry = 'YES'
      elif is_retry == 'NO' or is_retry == 'no' or is_retry == 'n' or is_retry == 'N':
        is_retry = 'NO'

    if is_retry == 'YES':
      loop_count += 1
    elif is_retry == 'NO':
      break
   
# ________________________________________________________________________________
#
# app実行
# ---------------------------

def initialize():
  """
  再実行用にglobal変数を再設定する
  """
  # ユーザ入力 >>> シャッフル元ページの取得件数
  global number_of_pages
  number_of_pages = int(input('シャッフル元となるページの取得件数を入力してください >>> '))
  
  # ユーザ入力 >>> 除外するドメインのリスト
  global user_input
  global exclusion_domain_list
  user_input = input('除外するドメインを指定してください（スペースを空けて複数指定可能） >>> ').strip() or None
  exclusion_domain_list = user_input and user_input.split() or []
  
  # 検索エンジンの指定
  global search_engine
  search_engine = 0
  while not search_engine in (1, 2, 3):
    search_engine = int(input('検索エンジンを選択してください。 1. Google, 2. Yahoo!, 3. Bing（1, 2, 3のどれかを押してください） >>> '))
  
  # ユーザ入力 >>> 検索キーワード
  global search_keyword
  search_keyword = '+'.join(input('検索キーワードを入力してください >>> ').split())
  
  # デフォルトの削除ドメイン
  default_exclusion_domain_list = ["https://www.amazon.co.jp/", "https://www.rakuten.co.jp/", "https://kakaku.com/", "https://twitter.com/", "https://www.instagram.com/", "https://www.cosme.net/", "https://beauty.hotpepper.jp/", "https://search.rakuten.co.jp/"]
  exclusion_domain_list.extend(default_exclusion_domain_list)
  
  # 必須KW
  global must_keyword
  must_keyword = input('必須キーワードを入力してください >>> ')

def app():
  """
  実行メソッド
  """
  while True:

    # マルコフ連鎖ツールの実行
    marcovify_headings_app()
    
    is_retry = ""
    while is_retry != 'YES' and is_retry != 'NO':
      is_retry = input('新たにキーワード等を指定して、見出し・本文の自動生成を行いますか？ ( YES / NO ) >>> ')
      if is_retry == 'YES' or is_retry == 'yes' or is_retry == 'y' or is_retry == 'Y':
        is_retry = 'YES'
      elif is_retry == 'NO' or is_retry == 'no' or is_retry == 'n' or is_retry == 'N':
        is_retry = 'NO'
    
    if is_retry == 'YES':
      initialize()
      continue
    elif is_retry == 'NO':
      break

# 処理実行
app()