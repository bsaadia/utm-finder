# UTM Finder

A simple web app that returns the UTM zone and CRS for any location on Earth.

## Features

- **Click on map** — click anywhere on the interactive map to get the UTM zone
- **Search by place name** — type a location to look it up
- **Upload a file** — upload a KML/KMZ file to detect its UTM zone

## Run locally with Docker

```bash
docker build -t utm-finder .
docker run -p 5001:5000 utm-finder
```

Then open [http://localhost:5001](http://localhost:5001).

## Run locally

```bash
pip install -r requirements.txt
flask run
```

## Stack

- Flask, Gunicorn
- Leaflet.js
