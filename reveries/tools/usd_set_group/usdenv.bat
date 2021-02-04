@echo off
echo off

set USDFILEPATH=%1
:: set USDFILEPATH=F:\usd\test\usd_avalon\reveries-config\reveries\tools\usd_set_group\core.py

set PATH=Q:\Resource\USD\lib;Q:\Resource\USD\bin;%PATH%
set PATH=T:\third-party\python27\;T:\third-party\python27\Scripts\;%PATH%

set PYTHONPATH=Q:\Resource\USD\lib\python\;%PYTHONPATH%


set VAR_2=%2
:: set VAR_2="{'BillboardGroup': {'BillboardA': {'asset_usd_file_path':r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'},'BillboardB': {'asset_usd_file_path':r'Q:\199909_AvalonPlay\Avalon\PropBox\BoxB\publish\assetPrim\v002\USD\asset_prim.usda'}}}"

set SAVE_PATH=%3
:: set SAVE_PATH=C:/Users/rebeccalin209/Desktop/BoxGroup_3.usda

set JSON_PATH=%4

python %USDFILEPATH% set_data=%VAR_2% usd_save_path=%SAVE_PATH% json_save_path=%JSON_PATH%
