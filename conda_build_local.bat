@echo off
call conda build conda_recipe -c conda-forge -c defaults
pause
if errorlevel 1 (
    echo.
    echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo !!!!!!!! Errors occured !!!!!!!!!!
    echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo .
    ) else (
    echo.
    echo **********************************
    echo ************** YES! **************
    echo **********************************
    echo Build complete
    echo package placed in your local channel, typically located at:
    echo C:\Users\%username%\AppData\Local\Continuum\Anaconda3\conda-bld
    echo.
    )
echo on

pause