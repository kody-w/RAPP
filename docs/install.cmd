@echo off
setlocal EnableExtensions
REM RAPP_RESTORED_SOURCE_COMMIT=4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6
REM RAPP_RESTORED_SOURCE_BLOB=03506ae1ab55d666f8fc47e9248afe4a54e15c72
REM RAPP_RESTORED_TARGET=docs/install.cmd
set "_rapp_target=docs/install.cmd"
set "_rapp_commit=4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"
set "_rapp_blob=03506ae1ab55d666f8fc47e9248afe4a54e15c72"
set "_rapp_pin_sha256=427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
if "%~1"=="" goto rapp_plan
if /I "%~1"=="plan" goto rapp_plan
if /I "%~1"=="--plan" goto rapp_plan
if /I "%~1"=="inspect" goto rapp_plan
if /I "%~1"=="--inspect" goto rapp_plan
if /I "%~1"=="check" goto rapp_plan
if /I "%~1"=="--check" goto rapp_plan
if /I "%~1"=="help" goto rapp_plan
if /I "%~1"=="--help" goto rapp_plan
if /I "%~1"=="-h" goto rapp_plan
if /I "%~1"=="apply" goto rapp_activate
if /I "%~1"=="--apply" goto rapp_activate
if /I "%~1"=="run" goto rapp_activate
if /I "%~1"=="--run" goto rapp_activate
goto rapp_bad_mode

:rapp_activate
shift
set "_rapp_allow=0"
set "_rapp_requested_target="
set "_rapp_pin="
set "_rapp_injection="
set "_rapp_approval="
set "_rapp_evidence="
:rapp_parse
if "%~1"=="" goto rapp_validate
if /I "%~1"=="--allow-active-effects" (
    set "_rapp_allow=1"
    shift
    goto rapp_parse
)
if "%~2"=="" goto rapp_missing_value
if /I "%~1"=="--target" set "_rapp_requested_target=%~2"
if /I "%~1"=="--kernel-pin" set "_rapp_pin=%~2"
if /I "%~1"=="--reviewed-dependency-injection" set "_rapp_injection=%~2"
if /I "%~1"=="--owner-approval" set "_rapp_approval=%~2"
if /I "%~1"=="--section13-evidence" set "_rapp_evidence=%~2"
if /I not "%~1"=="--target" if /I not "%~1"=="--kernel-pin" if /I not "%~1"=="--reviewed-dependency-injection" if /I not "%~1"=="--owner-approval" if /I not "%~1"=="--section13-evidence" goto rapp_unsupported
shift
shift
goto rapp_parse

:rapp_validate
if not "%_rapp_allow%"=="1" goto rapp_missing_allow
if /I not "%_rapp_requested_target%"=="%_rapp_target%" goto rapp_bad_target
if not exist "%_rapp_pin%" goto rapp_bad_pin
for %%I in ("%_rapp_pin%") do set "_rapp_pin_full=%%~fI"
for %%I in ("%~dp0..\KERNEL_PIN.json") do set "_rapp_expected_pin=%%~fI"
if /I not "%_rapp_pin_full%"=="%_rapp_expected_pin%" goto rapp_bad_pin
if not exist "%_rapp_injection%" goto rapp_missing_injection
if exist "%_rapp_injection%\NUL" goto rapp_missing_injection
if not exist "%_rapp_approval%" goto rapp_missing_approval
if exist "%_rapp_approval%\NUL" goto rapp_missing_approval
if not exist "%_rapp_evidence%" goto rapp_missing_evidence
if exist "%_rapp_evidence%\NUL" goto rapp_missing_evidence
goto rapp_no_authority

:rapp_plan
echo {"schema":"rapp-restored-distribution-source/1.0","target":"%_rapp_target%","mode":"plan","source_commit":"%_rapp_commit%","source_blob":"%_rapp_blob%","kernel":"kody-w/rapp-installer@brainstem-v0.6.9","kernel_pin_sha256":"%_rapp_pin_sha256%","apply_permitted":false,"reason":"authenticated-section-13-evidence-unavailable"}
exit /b 0
:rapp_bad_mode
1>&2 echo 410 Gone: %_rapp_target%: explicit plan/check/inspect or gated --apply is required ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_missing_value
1>&2 echo 410 Gone: %_rapp_target%: missing activation option value ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_unsupported
1>&2 echo 410 Gone: %_rapp_target%: unsupported activation argument ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_missing_allow
1>&2 echo 410 Gone: %_rapp_target%: --allow-active-effects is required ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_bad_target
1>&2 echo 410 Gone: %_rapp_target%: target-specific approval target is missing or mismatched ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_bad_pin
1>&2 echo 410 Gone: %_rapp_target%: exact KERNEL_PIN.json for kody-w/rapp-installer@brainstem-v0.6.9 is required ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_missing_injection
1>&2 echo 410 Gone: %_rapp_target%: reviewed dependency injection evidence is required ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_missing_approval
1>&2 echo 410 Gone: %_rapp_target%: target-specific owner approval is required ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_missing_evidence
1>&2 echo 410 Gone: %_rapp_target%: authenticated fresh section-13 evidence is required ^(RAPP1_STATUS.md^).
exit /b 78
:rapp_no_authority
1>&2 echo 410 Gone: %_rapp_target%: authenticated fresh section-13 evidence is unavailable ^(RAPP1_STATUS.md^).
exit /b 78
REM RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN
@echo off
REM RAPP Brainstem Installer for Windows CMD
REM Launches the PowerShell installer

echo.
echo   RAPP Brainstem Installer
echo   ========================
echo.
echo   Launching installer...
echo.

powershell -ExecutionPolicy Bypass -Command "& { irm https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.ps1 | iex }"

if %ERRORLEVEL% neq 0 (
    echo.
    echo   Installation failed. Try running install.ps1 directly in PowerShell.
    echo.
    pause
    exit /b 1
)

echo.
echo   Installation complete!
echo   Open a new terminal and run: brainstem
echo.
pause
