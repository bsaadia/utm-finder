# CLAUDE.md

## Project

`utm_finder` — a lightweight Flask + Leaflet webapp that tells you the UTM zone for any location on Earth.

## What it does

- Click anywhere on a Leaflet map → returns UTM zone + CRS
- Search a place name → returns UTM zone + CRS
- Upload a WGS84 file → detect UTM zone + CRS

## What it does NOT do

- No file output or downloads
- No complex UI — keep it minimal and fast

## Stack

- **Backend:** Python, Flask
- **Frontend:** Leaflet.js, minimal HTML/CSS/JS
- **Processing:** all local, no external APIs for computation

## Target user

Someone who needs to quickly look up the UTM zone of a location — no GIS expertise assumed.
