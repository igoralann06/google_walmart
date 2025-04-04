@echo off
echo main server
start cmd /k python app.py

echo google server
cd google_api
start cmd /k python main.py
cd ..

echo walmart server
cd walmart_api
start cmd /k python main.py