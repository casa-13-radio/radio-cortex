# Radio Cortex

AI-powered curation agents for Creative Commons music.

## Overview

Radio Cortex is a multi-agent system for discovering, classifying, and curating Creative Commons music. It consists of autonomous agents that work together to build a rich catalog of legally streamable music.

## Agents

- **Hunter**: Discovers and collects CC-licensed music from various sources (Archive.org, Jamendo, etc.)
- **Librarian**: Enriches track metadata using AI (LLM for classification, embeddings for similarity)
- **Compliance Officer**: Validates license compliance (planned)
- **Taste-Maker**: Generates intelligent playlists (planned)

## Architecture

The system is built with:

- **Python 3.11** with AsyncIO
- **FastAPI** for the REST API
- **PostgreSQL** with pgvector for vector similarity search
- **Redis** for caching
- **Docker** for containerization

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Groq API key (for Librarian agent)

### Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/radio-cortex
   cd radio-cortex