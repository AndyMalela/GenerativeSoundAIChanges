# IEEE Game Sound Design for Accessibility

This project was a 2025 IEEE Competition entry designing sound design targeting visually impaired users in a fighting game environment 'FightingICE'. The objective is to develop spatial and functional sound design strategies that support blind and visually impaired users in experiencing a game.

Details for the 'DareFightingICE' sound design competition is [here](https://cog2025.inesc-id.pt/darefightingice-ai-competition/). Details about the game itself and the competition rules is [here](https://github.com/TeamFightingICE/FightingICE/tree/master/DareFightingICE/Sound) and [here](https://www.ice.ci.ritsumei.ac.jp/~ftgaic/).

# Installation Quick Guide (latest update 2025)

## Prerequisites

Before setting up the project, ensure you have Python 3.12 installed on your system.

## Quickstart with Docker

- Boot DareFightingICE
- Run the docker container
```
docker run -it --rm -e SERVER_HOST=host.docker.internal ghcr.io/teamfightingice/generative-sound-ai
```

## Instruction

__1. Install dependencies with pip__
```
pip install -r requirements.txt
```

__2. Install OpenAL Soft__

- For Windows, please copy the DLL files in `lib/windows` to `C:/Windows/System32` folder.

- For Linux (Ubuntu, other distros should be similar)
```
sudo apt-add-repository universe
sudo apt-get update
sudo apt-get install libopenal-dev makehrtf openal-info
```

- For MacOS
```
brew install openal-soft
echo 'export DYLD_LIBRARY_PATH="/opt/homebrew/opt/openal-soft/lib:$DYLD_LIBRARY_PATH"' >> ~/.zshrc
```

__3. Run the generative sound AI__
- Boot [DareFightingICE](https://github.com/TeamFightingICE/FightingICE/releases/tag/v7.0)
- Execute `main.py`
```
python main.py
```
