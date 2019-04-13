# coding: utf-8
# cx_Freeze 用セットアップファイル
 
import sys
from cx_Freeze import setup, Executable
import requests
 
base = None

## GUI=有効, CUI=無効 にする
#if sys.platform == 'win32' : base = 'Win32GUI'
 
# exe にしたい python ファイルを指定
exe = Executable(script = 'shuffle_headings.py', icon = "python_01.ico", base = base)

# セットアップ
setup(name = 'shuffle_headings',
  version = '0.1',
  description = 'converter',
  executables = [exe],
  options = {
    "build_exe":{
      "packages": [
        "multiprocessing"
      ],
      "include_files":[
        "c:/Users/atno1/Desktop/適当なもの置き場/エンジニア箱/ツール系/ve_python3.6/Scripts/python36.dll",
        "c:/Users/atno1/Desktop/適当なもの置き場/エンジニア箱/ツール系/ve_python3.6/Lib/site-packages/idna",
        (requests.certs.where(),"cacert.pem")
      ]
    }
  }
)
