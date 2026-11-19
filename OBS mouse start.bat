
@echo off
title OBS Mouse Visualiser
cd /d "%~dp0"

REM =================================
REM CURSOR SIZE
REM =================================

set BASE_SIZE=1.5
set CLICK_SIZE=0.6

REM =================================
REM ANIMATION TIMING (SECONDS)
REM =================================

set SHRINK_TIME=0.35
set GROW_TIME=0.35

REM =================================
REM CURSOR POSITION OFFSET
REM =================================

set TIP_X=0
set TIP_Y=0
// offset pixels of mouse pointers

REM =================================
REM TRACKING SPEED
REM =================================

set UPDATE_MS=0

REM =================================
REM ANIMATION INTERPOLATION
REM 0 = LINEAR LERP
REM 1 = SMOOTHSTEP
REM =================================

set SMOOTHSTEP=0 
// type of mouse minimization lerp vs smoothstep

REM =================================
REM NATIVE CURSOR
REM 1 = HIDE WINDOWS CURSOR
REM 0 = KEEP WINDOWS CURSOR
REM =================================

set HIDE_NATIVE_CURSOR=1

python mouse_visualiser.py

if errorlevel 1 pause
