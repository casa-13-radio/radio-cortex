# 🧪 Testing Guide - Radio Cortex

## 1. Setup Inicial

### 1.1 Instalar Dependências

```bash
# Clone o repositório
git clone https://github.com/yourusername/radio-cortex
cd radio-cortex

# Criar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -e .[dev]
```

### 1.2 Configurar Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env com suas credenciais
nano .env
```

**Variáveis obrigatórias:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://cortex:password@localhost:5432/radiocortex

# APIs
GROQ_API_KEY=gsk_xxx  # Obter em https://console.groq.com

# Storage (opcional para MVP)
# OCI_STORAGE_BUCKET=radiocasa13-audio
```

### 1.3 Subir Infraestrutura Local

```bash
# Subir PostgreSQL + Redis
docker-compose up -d postgres redis

# Aguardar serviços ficarem saudáveis
docker-compose ps

# Rodar migrações
make db-migrate

# (Opcional) Popular com dados de exemplo
make db-seed
```

---

## 2. Testando Localmente (Desenvolvimento)

### 2.1 Testes Unitários

**Rodar todos os testes:**
```bash
make test
# ou
pytest
```

**Rodar testes de um agente específico:**
```bash
pytest tests/unit/test_hunter.py -v
pytest tests/unit/test_librarian.py -v
```

**Com coverage:**
```bash
make test-cov
# Abre htmlcov/index.html no navegador
```

**Rodar apenas testes rápidos (skip slow tests):**
```bash
pytest -m "not slow"
```

### 2.2 Testando Hunter Agent

#### Teste 1: Coletar de Archive.org (Dry Run)

```bash
# Não baixa arquivos, só mostra o que seria coletado
python -m agents.hunter --source archive.org --dry-run --log-level DEBUG
```

**Saída esperada:**
```
2024-11-24 10:00:00 - hunter_agent - INFO - Hunter Agent starting
2024-11-24 10:00:01 - hunter_agent - INFO - Fetching RSS: https://archive.org/...
2024-11-24 10:00:02 - hunter_agent - INFO - Found 20 entries in RSS
2024-11-24 10:00:03 - hunter_agent - DEBUG - Track: "Artist - Title", License: CC-BY
2024-11-24 10:00:03 - hunter_agent - DEBUG - Track: "Artist2 - Title2", License: CC0
...
```

#### Teste 2: Coletar de Verdade (1 faixa)

```bash
# Coletar apenas 1 faixa para testar o fluxo completo
python -m agents.hunter --source archive.org --max-tracks 1
```

**Verificar resultado:**
```bash
# Checar se arquivo foi baixado
ls -lh /tmp/hunter_downloads/

# Checar se foi salvo no banco
psql -d radiocortex -c "SELECT title, artist, status FROM tracks;"
```

#### Teste 3: Rodar como Daemon (Background)

```bash
# Em um terminal separado
python -m agents.hunter --daemon --log-level INFO
```

**Monitorar logs:**
```bash
tail -f logs/hunter.log
```

**Parar o daemon:**
```bash
# Ctrl+C no terminal
# ou
pkill -f "agents.hunter"
```

### 2.3 Testando Librarian Agent

#### Teste 1: Processar 1 Track Pendente

```bash
# Primeiro, garantir que há tracks pendentes
python -c "from models.track import Track; from models.database import get_session; \
           session = get_session(); \
           print(session.query(Track).filter(Track.status=='pending_enrichment').count())"

# Rodar Librarian
python -m agents.librarian --max-tracks 1
```

**Verificar resultado:**
```bash
psql -d radiocortex -c "
  SELECT 
    title, 
    primary_genre, 
    mood_tags, 
    status 
  FROM tracks 
  WHERE status = 'pending_compliance';
"
```

#### Teste 2: Testar Classificação de Gênero

```python
# tests/manual/test_librarian_classification.py
from agents.librarian.agent import LibrarianAgent
from models.track import TrackMetadata

async def test_classification():
    agent = LibrarianAgent(config, db_session)
    
    metadata = TrackMetadata(
        title="Águas de Março",
        artist="Tom Jobim",
        license="CC-BY",
        source_url="https://example.com",
        audio_url="https://example.com/audio.mp3"
    )
    
    result = await agent.classify_track(metadata)
    
    print(f"Gênero: {result['genre']}")
    print(f"Mood: {result['mood']}")
    print(f"Contexto: {result['cultural_context']}")

# Rodar
python tests/manual/test_librarian_classification.py
```

### 2.4 Testando Integração Hunter → Librarian

```bash
# Terminal 1: Rodar Hunter (coleta 1 track)
python -m agents.hunter --source archive.org --max-tracks 1

# Terminal 2: Monitorar banco
watch -n 2 'psql -d radiocortex -c "SELECT title, status FROM tracks ORDER BY created_at DESC LIMIT 5;"'

# Terminal 3: Rodar Librarian (processa track coletado)
python -m agents.librarian --daemon
```

**Fluxo esperado:**
1. Hunter coleta track → status = `pending_enrichment`
2. Librarian pega track → gera embeddings → status = `pending_compliance`
3. (Futuro) Compliance valida → status = `approved`

### 2.5 Testando Busca Semântica (pgvector)

```bash
# Via CLI
python scripts/test_semantic_search.py --query "chill brazilian jazz"
```

**Ou via Python:**
```python
from services.search import SemanticSearch

search = SemanticSearch(db_session)
results = await search.query("chill brazilian jazz", limit=10)

for track, similarity in results:
    print(f"{track.title} - {track.artist} (similarity: {similarity:.2f})")
```

---

## 3. Testando em Ambiente Docker

### 3.1 Build e Run

```bash
# Build
make docker-build

# Subir tudo
make docker-up

# Ver logs
make docker-logs

# Entrar no container
make docker-shell
```

### 3.2 Rodar Testes Dentro do Container

```bash
# Entrar no container
docker-compose exec cortex bash

# Dentro do container
pytest
python -m agents.hunter --source archive.org --dry-run
```

---

## 4. Testes de Integração (End-to-End)

### 4.1 Teste Completo: Hunter → Librarian → API

```bash
# Arquivo: tests/integration/test_full_pipeline.py
pytest tests/integration/test_full_pipeline.py -v
```

**O que esse teste faz:**
1. Hunter coleta 1 track de Archive.org
2. Librarian processa (LLM + embeddings)
3. API retorna track via `/api/v1/tracks`
4. Busca semântica funciona

### 4.2 Teste de Carga (Stress Test)

```bash
# Coletar 100 tracks simultaneamente
python tests/integration/test_hunter_stress.py --tracks 100 --concurrency 10
```

**Métricas esperadas:**
- Taxa de sucesso: > 95%
- Tempo médio por track: < 30s
- Uso de memória: < 1GB

---

## 5. Testando em Produção (Staging/Prod)

### 5.1 Deploy para Staging

```bash
# Via GitHub Actions (automático ao fazer push para develop)
git push origin develop

# Ou manualmente
make deploy-dev
```

### 5.2 Smoke Tests em Staging

```bash
# Testar endpoints críticos
curl https://staging.radiocasa13.org/health
curl https://staging.radiocasa13.org/api/v1/tracks

# Testar busca
curl "https://staging.radiocasa13.org/api/v1/search?q=jazz"
```

### 5.3 Monitorar Logs de Produção

```bash
# SSH no servidor
ssh user@staging.radiocasa13.org

# Ver logs do Hunter
docker-compose logs -f cortex | grep hunter

# Ver logs do Librarian
docker-compose logs -f celery_worker
```

### 5.4 Testar Agente Manualmente em Produção

```bash
# SSH no servidor
ssh user@production.radiocasa13.org

# Entrar no container
docker-compose exec cortex bash

# Rodar Hunter manualmente (dry-run para segurança)
python -m agents.hunter --source archive.org --dry-run --max-tracks 5
```

---

## 6. Debugging

### 6.1 Hunter Não Encontra Tracks

**Problema:** `Found 0 tracks with valid license`

**Diagnóstico:**
```bash
# Ver RSS raw
curl https://archive.org/services/collection-rss.php?collection=audio | less

# Testar parser manualmente
python -c "
import feedparser
feed = feedparser.parse('https://...')
for entry in feed.entries[:5]:
    print(entry.get('title'), entry.get('rights'))
"
```

**Solução:** Ajustar regex de detecção de licença em `hunter_agent.py:_parse_license_string()`

### 6.2 Librarian Gera Classificações Ruins

**Problema:** Gênero sempre vem como "Pop" ou "Unknown"

**Diagnóstico:**
```bash
# Ver prompt enviado para LLM
python -m agents.librarian --log-level DEBUG --max-tracks 1 2>&1 | grep "LLM Prompt"
```

**Solução:** Refinar prompt em `agents/librarian/prompts.py`

### 6.3 Testes Falhando no CI

**Problema:** Testes passam localmente mas falham no GitHub Actions

**Diagnóstico:**
```bash
# Rodar localmente com mesmas condições do CI
docker run --rm -it python:3.11-slim bash
# Dentro do container
git clone https://github.com/yourusername/radio-cortex
cd radio-cortex
pip install -e .[dev]
pytest
```

**Solução:** Provavelmente problema com variáveis de ambiente ou dependências de sistema

---

## 7. Boas Práticas

### 7.1 Antes de Fazer Commit

```bash
# Rodar checagem completa
make ci-test

# Se tudo passar, pode commitar
git add .
git commit -m "feat: add Bandcamp spider"
git push
```

### 7.2 Escrever Novos Testes

**Para cada nova feature, adicione:**

1. **Teste unitário** (`tests/unit/`)
   - Testa função/classe isoladamente
   - Mock de dependências externas (DB, APIs)

2. **Teste de integração** (`tests/integration/`)
   - Testa fluxo completo
   - Usa banco de dados real (test database)

3. **Fixture de dados** (`tests/fixtures/`)
   - Dados de exemplo para testes

**Exemplo:**
```python
# tests/unit/test_new_feature.py
def test_parse_bandcamp_license():
    """Test Bandcamp license parser"""
    html = '<div class="license">CC BY-NC-SA</div>'
    license = parse_bandcamp_license(html)
    assert license == "CC-BY-NC-SA"
```

### 7.3 Coverage Mínimo

**Meta:** Manter coverage > 80%

```bash
# Ver coverage atual
pytest --cov=. --cov-report=term-missing

# Identificar código sem testes
coverage report --show-missing
```

---

## 8. Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| `ModuleNotFoundError: No module named 'agents'` | `pip install -e .` |
| `psycopg2.OperationalError: connection refused` | `docker-compose up -d postgres` |
| `groq.APIError: Invalid API key` | Verificar `GROQ_API_KEY` no `.env` |
| Testes lentos | `pytest -m "not slow"` ou `pytest -n auto` (pytest-xdist) |
| Docker sem espaço | `docker system prune -a` |
| Logs muito verbosos | Ajustar `LOG_LEVEL=INFO` no `.env` |

---

## 9. Checklist de QA (Antes de Release)

- [ ] Todos os testes unitários passando
- [ ] Testes de integração passando
- [ ] Coverage > 80%
- [ ] Sem warnings de linter
- [ ] Smoke tests em staging OK
- [ ] Logs sem erros críticos
- [ ] Performance aceitável (< 30s por track)
- [ ] Documentação atualizada
- [ ] CHANGELOG.md atualizado

---

## 10. Recursos Adicionais

**Documentação:**
- [pytest docs](https://docs.pytest.org/)
- [Docker Compose docs](https://docs.docker.com/compose/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)

**Ferramentas úteis:**
- `pytest-watch`: Auto-run tests on file change
- `pytest-xdist`: Run tests in parallel
- `hypothesis`: Property-based testing
- `locust`: Load testing

---

**Dúvidas?** Abra uma issue: https://github.com/yourusername/radio-cortex/issues