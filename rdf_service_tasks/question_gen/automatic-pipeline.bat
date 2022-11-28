@echo off


:begin

python service.py

timeout 4

goto begin
