FROM mcr.microsoft.com/devcontainers/universal
# work around https://github.com/devcontainers/images/issues/1752
RUN rm -f /etc/apt/sources.list.d/yarn.list
# install fontforge
RUN apt-get update && apt-get install -y --no-install-recommends \
    fontforge-nox \
    && rm -rf /var/lib/apt/lists/*
