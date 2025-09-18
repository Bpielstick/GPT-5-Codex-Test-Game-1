# Pixel Commanders

Pixel Commanders is a lightweight 2D pixel-art RTS sandbox inspired by classic Command & Conquer gameplay. Two AI commanders battle across procedurally generated battlefields while the user observes the action. The observer can pause, resume, or restart matches at any time.

## Features

- **Procedurally generated maps**: Large 128×128 tile maps with grasslands, forests, mountains, and lakes.
- **Autonomous AI combatants**: Two computer players manage resources, build armies, and attack enemy bases.
- **Pixel-art visuals**: Retro colour palette with dithering, unit sprites, and animated combat.
- **Observer controls**: On-screen buttons for pausing, resuming, and restarting matches, plus free camera panning with WASD/arrow keys.

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

Each restart generates a brand new procedural battlefield and resets both AIs.

## Project structure

- `main.py` – Pygame bootstrap and observer UI.
- `rts/` – Game modules for map generation, AI, entities, and rendering.
- `requirements.txt` – Python dependencies.

Enjoy spectating the battles!
