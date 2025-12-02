# Cortex — IA para Curadoria Cultural

> Sistema de agentes inteligentes para descoberta, análise e curadoria
> de música com licenças abertas

## Agentes

| Agente | Função | Status |
|--------|--------|--------|
| 🔍 Coletor | Busca músicas em Free Music Archive, Jamendo, etc | 🟢 Ativo |
| 📊 Analista | Extrai metadados via MusicBrainz/Discogs | 🟢 Ativo |
| ⚖️ Jurídico | Verifica licenças Creative Commons | 🟡 Beta |
| 🎵 Curador | Gera playlists temáticas com GPT | 🟡 Beta |
| 📈 Tendências | Analisa padrões de escuta | 🔴 Planejado |

## Arquitetura

```
┌───────────────┐     ┌──────────────┐     ┌───────────┐
│   API Radio   │────▶│    Cortex    │────▶│  Redis    │
│   (FastAPI)   │     │ (Orquestrador)│    │  (Filas)  │
└───────────────┘     └──────────────┘     └───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌───────────┐   ┌──────────┐
        │MusicBrainz│   │  OpenAI   │   │ Jamendo  │
        │   API    │   │   API     │   │   API    │
        └──────────┘   └───────────┘   └──────────┘
```

## Requisitos

- Python 3.11+
- Redis
- Chave de API: OpenAI (para curadoria avançada)

## Variáveis de ambiente

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/radio
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...  # Opcional, para agente Curador
MUSICBRAINZ_USER_AGENT=RadioCasa13/1.0
```

## Por que não modelos locais?

Optamos por APIs externas porque:
1. Rodamos em Oracle Free Tier (recursos limitados)
2. Custo de API é negligível para nosso volume (~$5/mês)
3. Manutenção de modelos locais é complexa
4. Foco do projeto é curadoria, não infraestrutura de ML
