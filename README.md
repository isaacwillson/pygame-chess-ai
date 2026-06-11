# pygame-chess-ai


# Description
A chess game built with Python and Pygame where players play against an AI opponent with adjustable difficulty levels. Includes complete chess gameplay and functionality, and an AI capable of making strategic decisions based on the state of the game and search algorithms.

# Demo 

# Installation 
Clone the repo and install dependencies:
```Bash
git clone https://github.com/isaacwillson/pygame-chess-ai.git
cd pygame-chess-ai
pip install -r requirements.txt
```

# Usage
python main.py

# Features
- Interactive chess board built with Pygame
- Clean user interphase
- AI opponent with Easy/Medium/Hard difficulty levels
- Legal move generation
- Move validation
- Check + Checkmate detection
- Board evaluation system for AI decision making

# AI Implementation
Algorithms:
- Minimax search
- Alpha-Beta Pruning
- Board Evaluation Function

Easy
- Limites search/minimax depth
- Faster move selection
- Likely to miss tactics

Medium:
- Increased search depth
- Better positional awareness
- Strong opponenet

Hard
- Deep search depth
- Advanced board evaluation
- Significantly challenging opponenet

# Tech Stack
- Python
- Pygame
