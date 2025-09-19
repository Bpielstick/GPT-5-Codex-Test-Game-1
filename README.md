# Pixel Commanders

Pixel Commanders is a fully automated 2D pixel-art RTS sandbox inspired by classic Command & Conquer gameplay. Two computer-controlled factions expand across procedural continents, gather resources, construct bases, unlock technology, and wage large scale battles while the player observes from a free camera. The observer can pause, resume, or restart matches at any time.

## Features

- **Procedurally generated warzones** – Vast 128×128 tile battlefields with mountains, forests, and inland lakes. The map generator guarantees land bridges between starting bases and scatters mineral caches to contest.
- **Complete RTS economy loop** – Engineers harvest resource nodes, unload at refineries or the HQ, and feed a production pipeline that unlocks new structures and units.
- **Structure building and tech progression** – AIs follow a construction plan from Command HQ through refineries, barracks, factories, and research labs, increasing their tech level as buildings finish.
- **Diverse combat units** – Infantry, rangers, tanks, and long-range artillery each have bespoke pixel-art silhouettes, movement speeds, and attack statistics.
- **Autonomous commanders** – Rival AIs balance expansion, army composition, and attack orders with adaptive retargeting.
- **Observer friendly UI** – WASD/arrow-key panning, animated pixel-art rendering, and on-screen buttons for Pause, Resume, and Restart.

## Requirements

- Python 3.10+
- [Pygame](https://www.pygame.org/) 2.0+

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the game

```bash
python main.py
```

Controls:

- **WASD / Arrow keys** – Pan the camera.
- **Pause / Resume / Restart buttons** – Control match flow.
- **Esc / Window close** – Quit the game.

Each restart generates a brand new procedural battlefield, respawns both factions, and kicks off a fresh war.

## Project structure

- `main.py` – Pygame bootstrap and observer UI.
- `rts/` – Game modules for map generation, AI, entities, and rendering.
- `requirements.txt` – Python dependencies.

Enjoy spectating the battles!
