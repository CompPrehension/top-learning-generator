@echo off
rem example cmd :
rem run_q_generator_main.bat -i "c:/data/compp-gen/control_flow/parsed" -o "c:/data/compp-gen/control_flow/questions" -g "ag" -n 5
rem (the same, using long option names:)
rem run_q_generator_main.bat --input "c:/data/compp-gen/control_flow/parsed" --output "c:/data/compp-gen/control_flow/questions" --origin "ag" --limit 5

rem quick help: → %* ← means pass all recieved cmd args to child command.
@echo on

python %~dp0/q_generator_main.py %*
