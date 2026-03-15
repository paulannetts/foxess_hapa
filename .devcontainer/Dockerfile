FROM mcr.microsoft.com/devcontainers/python:2.1.2-3.14-bookworm

# Update package lists and install desired packages
RUN apt-get update && apt-get install -y \
    ffmpeg libturbojpeg0 libpcap-dev \
    && rm -rf /var/lib/apt/lists/*
