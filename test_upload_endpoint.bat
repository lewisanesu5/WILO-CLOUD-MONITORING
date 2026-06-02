@echo off
REM Test script for Remote Sensor Upload Endpoint

echo.
echo ============================================
echo Testing Secure Upload Endpoint
echo ============================================
echo.

REM Test 1: Health Check
echo [Test 1] Health Check
echo URL: http://localhost:5001/health
curl -s http://localhost:5001/health | powershell -Command "ConvertFrom-Json | ConvertTo-Json"
echo.

REM Test 2: Test with Valid API Key
echo [Test 2] Upload with Valid API Key
echo Uploading 2 CSV files...
curl -X POST http://localhost:5001/api/upload ^
  -H "X-API-Key: sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b" ^
  -F "files=@Data/max_acceleration.csv" ^
  -F "files=@Data/min_acceleration.csv" | powershell -Command "ConvertFrom-Json | ConvertTo-Json -Depth 3"
echo.

REM Test 3: Check Upload Status
echo [Test 3] Check Upload Status
echo URL: http://localhost:5001/api/upload/status
curl -s http://localhost:5001/api/upload/status | powershell -Command "ConvertFrom-Json | ConvertTo-Json -Depth 2"
echo.

REM Test 4: Test Invalid API Key (Should Fail)
echo [Test 4] Test Invalid API Key (Should Fail with 403)
curl -X POST http://localhost:5001/api/upload ^
  -H "X-API-Key: invalid-key-12345" ^
  -F "files=@Data/max_acceleration.csv" ^
  -F "files=@Data/min_acceleration.csv" | powershell -Command "ConvertFrom-Json | ConvertTo-Json"
echo.

echo ============================================
echo All Tests Complete!
echo ============================================
